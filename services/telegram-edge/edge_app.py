#!/usr/bin/env python3
"""Stateless, transport-only Telegram Edge for A.I. My Time TE-1.

The process never persists updates, users, messages, or business state.  It
accepts only the Telegram webhook and a small authenticated Core relay API.
It deliberately logs metadata only; request and response bodies never enter
the log stream.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Mapping

MAX_BODY_BYTES = 1_048_576
ALLOWED_OPERATIONS = frozenset({
    "sendMessage",
    "answerCallbackQuery",
    "sendChatAction",
    "getMe",
    # This is a narrowly scoped, authenticated cutover control.  It never
    # accepts a caller-supplied URL or secret: both remain Edge-local.
    "configureWebhook",
    "getWebhookInfo",
})


class EdgeConfigurationError(RuntimeError):
    """Configuration is incomplete; values must never be included in errors."""


@dataclass(frozen=True)
class EdgeConfig:
    bot_token: str
    telegram_webhook_secret: str
    core_to_edge_secret: str
    edge_to_core_secret: str
    core_webhook_url: str
    public_webhook_url: str

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "EdgeConfig":
        values = os.environ if environ is None else environ
        credentials_dir = values.get("CREDENTIALS_DIRECTORY", "")
        if not credentials_dir:
            raise EdgeConfigurationError("credential directory is not configured")

        def credential(name: str) -> str:
            try:
                with open(os.path.join(credentials_dir, name), encoding="utf-8") as handle:
                    value = handle.read().strip()
            except OSError as error:
                raise EdgeConfigurationError("required credential is unavailable") from error
            if not value:
                raise EdgeConfigurationError("required credential is empty")
            return value

        core_webhook_url = values.get("EDGE_CORE_WEBHOOK_URL", "").strip()
        if not core_webhook_url.startswith("https://"):
            raise EdgeConfigurationError("core webhook URL must use HTTPS")
        public_webhook_url = values.get(
            "EDGE_PUBLIC_WEBHOOK_URL", "https://edge.aimytimebot.ru/webhooks/telegram/lead"
        ).strip()
        if not public_webhook_url.startswith("https://"):
            raise EdgeConfigurationError("public webhook URL must use HTTPS")
        return cls(
            bot_token=credential("telegram_bot_token"),
            telegram_webhook_secret=credential("telegram_webhook_secret"),
            core_to_edge_secret=credential("core_to_edge_secret"),
            edge_to_core_secret=credential("edge_to_core_secret"),
            core_webhook_url=core_webhook_url,
            public_webhook_url=public_webhook_url,
        )


HttpRequest = Callable[[str, bytes, Mapping[str, str]], tuple[int, bytes]]


def _request(url: str, body: bytes, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_BODY_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionError("upstream connection failed") from error


class EdgeService:
    def __init__(self, config: EdgeConfig, requester: HttpRequest = _request) -> None:
        self._config = config
        self._request = requester

    def accept_webhook(self, body: bytes, telegram_secret: str) -> int:
        if not hmac.compare_digest(telegram_secret, self._config.telegram_webhook_secret):
            return HTTPStatus.UNAUTHORIZED
        if not _json_object(body):
            return HTTPStatus.BAD_REQUEST
        try:
            status, _ = self._request(
                self._config.core_webhook_url,
                body,
                {
                    "Content-Type": "application/json",
                    "X-Telegram-Bot-Api-Secret-Token": self._config.telegram_webhook_secret,
                    "X-Aimytime-Edge-Auth": self._config.edge_to_core_secret,
                },
            )
        except ConnectionError:
            return HTTPStatus.BAD_GATEWAY
        # Telegram must retry unless Core has durably accepted the update.
        return HTTPStatus.NO_CONTENT if 200 <= status < 300 else HTTPStatus.BAD_GATEWAY

    def invoke_telegram(self, operation: str, body: bytes, core_secret: str) -> tuple[int, dict[str, object]]:
        if not hmac.compare_digest(core_secret, self._config.core_to_edge_secret):
            return HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"}
        if operation not in ALLOWED_OPERATIONS:
            return HTTPStatus.NOT_FOUND, {"ok": False, "error": "operation_not_allowed"}
        if not _json_object(body):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_request"}
        # The configuration endpoints intentionally ignore their JSON object.
        # The URL and Telegram secret are fixed by this local Edge service,
        # not supplied by Core or an Internet client.
        telegram_operation = operation
        telegram_body = body
        if operation == "configureWebhook":
            telegram_operation = "setWebhook"
            telegram_body = json.dumps(
                {
                    "url": self._config.public_webhook_url,
                    "secret_token": self._config.telegram_webhook_secret,
                    "allowed_updates": ["message", "callback_query"],
                    "drop_pending_updates": False,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        elif operation == "getWebhookInfo":
            telegram_operation = "getWebhookInfo"
            telegram_body = b"{}"
        try:
            status, response = self._request(
                f"https://api.telegram.org/bot{self._config.bot_token}/{telegram_operation}",
                telegram_body,
                {"Content-Type": "application/json"},
            )
        except ConnectionError:
            return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "telegram_unavailable"}
        if not 200 <= status < 300:
            return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "telegram_rejected"}
        try:
            decoded = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "telegram_invalid_response"}
        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "telegram_rejected"}
        # Do not relay Telegram response content: it can contain operational
        # data and is unnecessary to Core.  A boolean success is enough.
        return HTTPStatus.OK, {"ok": True}


def _json_object(body: bytes) -> bool:
    if not body or len(body) > MAX_BODY_BYTES:
        return False
    try:
        return isinstance(json.loads(body.decode("utf-8")), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def make_handler(service: EdgeService) -> type[BaseHTTPRequestHandler]:
    class EdgeHandler(BaseHTTPRequestHandler):
        server_version = "AIMyTimeTelegramEdge/1"

        def log_message(self, fmt: str, *args: object) -> None:
            # No body, token, Telegram user identifier, or Core response is logged.
            sys.stderr.write(f"edge method={self.command} path={self.path.split('?', 1)[0]} status={getattr(self, '_status', 0)} latency_ms={getattr(self, '_latency_ms', 0)} request_id={getattr(self, '_request_id', '-')!s}\n")

        def do_GET(self) -> None:
            self._begin()
            if self.path == "/healthz":
                self._respond(HTTPStatus.OK, {"status": "ok", "service": "aimytime-telegram-edge"})
            else:
                self._respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            self._begin()
            body = self._body()
            if body is None:
                return
            if self.path == "/webhooks/telegram/lead":
                status = service.accept_webhook(body, self.headers.get("X-Telegram-Bot-Api-Secret-Token", ""))
                self._respond(status, None)
                return
            prefix = "/v1/telegram/"
            if self.path.startswith(prefix):
                operation = self.path[len(prefix):]
                status, result = service.invoke_telegram(operation, body, self.headers.get("X-Aimytime-Edge-Auth", ""))
                self._respond(status, result)
                return
            self._respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def _begin(self) -> None:
            self._started = time.monotonic()
            self._request_id = self.headers.get("X-Request-Id") or secrets.token_hex(8)
            self._status = 0
            self._latency_ms = 0

        def _body(self) -> bytes | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = MAX_BODY_BYTES + 1
            if content_length <= 0 or content_length > MAX_BODY_BYTES:
                self._respond(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_body_size"})
                return None
            return self.rfile.read(content_length)

        def _respond(self, status: int, payload: dict[str, object] | None) -> None:
            self._status = int(status)
            self._latency_ms = int((time.monotonic() - self._started) * 1000)
            self.send_response(status)
            self.send_header("X-Request-Id", self._request_id)
            if payload is None:
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return EdgeHandler


def main() -> None:
    config = EdgeConfig.from_environment()
    host = os.environ.get("EDGE_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("EDGE_BIND_PORT", "19113"))
    server = ThreadingHTTPServer((host, port), make_handler(EdgeService(config)))
    server.serve_forever()


app = EdgeService  # Allows the service contract to identify this module without a framework dependency.

if __name__ == "__main__":
    main()
