#!/usr/bin/env python3
"""Stateless, transport-only Telegram Edge for A.I. My Time TE-1.

The process never persists updates, users, messages, or business state.  It
accepts a Telegram webhook or explicitly selected official long polling, plus
a small authenticated Core relay API. Poll offsets advance only after durable
Core acknowledgement; a crash can replay an update, never silently discard it.
It deliberately logs metadata only; request and response bodies never enter
the log stream.
"""

from __future__ import annotations

import hmac
import http.client
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
    # Q1.1: a single fixed native commands-menu entrypoint and its narrow
    # read-back verification.  The payload is pinned below, so Core cannot
    # register arbitrary commands or menu buttons through this relay.
    "setMyCommands",
    "setChatMenuButton",
    "getMyCommands",
    "getChatMenuButton",
})
_MENU_COMMANDS = [{"command": "menu", "description": "Открыть доступные действия"}]
_MENU_BUTTON = {"type": "commands"}


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
    update_mode: str = "webhook"

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
        mode = values.get("EDGE_UPDATE_MODE", "")
        runtime_file = Path(__file__).with_name("runtime.json")
        if not mode and environ is None and runtime_file.exists():
            try:
                runtime = json.loads(runtime_file.read_text())
                if set(runtime) != {"update_mode"}:
                    raise ValueError("unexpected runtime settings")
                mode = runtime["update_mode"]
            except (ValueError, TypeError, OSError):
                raise EdgeConfigurationError("invalid runtime settings") from None
        mode = mode or "webhook"
        if not isinstance(mode, str) or mode not in {"webhook", "polling"}:
            raise EdgeConfigurationError("invalid update mode")
        return cls(
            bot_token=credential("telegram_bot_token"),
            telegram_webhook_secret=credential("telegram_webhook_secret"),
            core_to_edge_secret=credential("core_to_edge_secret"),
            edge_to_core_secret=credential("edge_to_core_secret"),
            core_webhook_url=core_webhook_url,
            public_webhook_url=public_webhook_url,
            update_mode=mode,
        )


HttpRequest = Callable[[str, bytes, Mapping[str, str]], tuple[int, bytes]]


def _create_ipv6_connection(
    address: tuple[str, int],
    timeout: object = socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address: tuple[str, int] | None = None,
) -> socket.socket:
    host, port = address
    last_error: OSError | None = None
    for family, socktype, proto, _, sockaddr in socket.getaddrinfo(
        host,
        port,
        socket.AF_INET6,
        socket.SOCK_STREAM,
    ):
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as error:
            last_error = error
            if sock is not None:
                sock.close()
    if last_error is not None:
        raise last_error
    raise OSError("no IPv6 address available")


class _IPv6HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._create_connection = _create_ipv6_connection


class _IPv6HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request: urllib.request.Request):
        return self.do_open(
            _IPv6HTTPSConnection,
            request,
            context=self._context,
        )


_TELEGRAM_IPV6_OPENER = urllib.request.build_opener(_IPv6HTTPSHandler())


def _request(url: str, body: bytes, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers))
    telegram_api = urllib.parse.urlsplit(url).hostname == "api.telegram.org"
    try:
        if telegram_api:
            response_context = _TELEGRAM_IPV6_OPENER.open(request, timeout=15)
        else:
            response_context = urllib.request.urlopen(request, timeout=15)
        with response_context as response:
            return response.status, response.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_BODY_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionError("upstream connection failed") from error


class EdgeService:
    def __init__(self, config: EdgeConfig, requester: HttpRequest = _request) -> None:
        self._config = config
        self._request = requester
        self.ingress: PollingIngress | None = None

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
        if operation == "configureWebhook" and self._config.update_mode == "polling":
            return HTTPStatus.CONFLICT, {"ok": False, "error": "polling_mode_active"}
        if not _json_object(body):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_request"}
        if not _valid_menu_request(operation, body):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_menu_request"}
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
        if operation == "getMyCommands" and decoded.get("result") != _MENU_COMMANDS:
            return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "menu_verification_failed"}
        if operation == "getChatMenuButton":
            menu_button = decoded.get("result")
            if not isinstance(menu_button, dict) or menu_button.get("type") != "commands":
                return HTTPStatus.BAD_GATEWAY, {"ok": False, "error": "menu_verification_failed"}
        # Do not relay Telegram response content: it can contain operational
        # data and is unnecessary to Core.  A boolean success is enough.
        return HTTPStatus.OK, {"ok": True}


class PollingIngress:
    """Official Telegram pull transport, with Core-before-Telegram ACK order."""

    def __init__(self, service: EdgeService) -> None:
        self.service = service
        self.offset = 0
        self.initialized = False
        self.last_poll = 0.0
        self.accepted = 0
        self.blocked = False
        self.stop = threading.Event()

    def telegram(self, method: str, payload: dict) -> object:
        config = self.service._config
        status, raw = self.service._request(
            f"https://api.telegram.org/bot{config.bot_token}/{method}",
            json.dumps(payload, separators=(",", ":")).encode(),
            {"Content-Type": "application/json"},
        )
        if status != 200 or len(raw) > MAX_BODY_BYTES:
            raise ConnectionError("telegram polling unavailable")
        try:
            decoded = json.loads(raw)
            if not isinstance(decoded, dict) or decoded.get("ok") is not True:
                raise ValueError("invalid telegram result")
            return decoded["result"]
        except (ValueError, KeyError, TypeError):
            raise ConnectionError("telegram polling response invalid") from None

    def initialize(self) -> None:
        info = self.telegram("getWebhookInfo", {})
        if not isinstance(info, dict) or info.get("url") not in {"", self.service._config.public_webhook_url}:
            raise ConnectionError("unexpected webhook owner")
        if info["url"]:
            # Never purge queued updates. Only the same Edge webhook may be
            # replaced. No public relay operation can change these arguments.
            if self.telegram("deleteWebhook", {"drop_pending_updates": False}) is not True:
                raise ConnectionError("webhook switch unconfirmed")
        self.initialized = True

    def poll_once(self) -> None:
        batch = self.telegram("getUpdates", {"offset": self.offset, "timeout": 8,
            "limit": 10, "allowed_updates": ["message", "callback_query"]})
        if not isinstance(batch, list):
            raise ConnectionError("invalid update batch")
        previous = self.offset - 1
        for item in batch:
            if not isinstance(item, dict) or type(item.get("update_id")) is not int or item["update_id"] <= previous:
                raise ConnectionError("invalid update sequence")
            previous = item["update_id"]
        self.last_poll = time.monotonic()
        for item in batch:
            raw = json.dumps(item, separators=(",", ":")).encode()
            status = self.service.accept_webhook(raw, self.service._config.telegram_webhook_secret)
            if status != HTTPStatus.NO_CONTENT:
                self.blocked = True
                raise ConnectionError("core acknowledgement not confirmed")
            # Only the NEXT getUpdates call acknowledges this prefix at Telegram.
            # Offset is intentionally not persisted: restart replays only the
            # unconfirmed tail, which Core must handle idempotently.
            self.offset = item["update_id"] + 1
            self.accepted += 1
        self.blocked = False

    def healthy(self) -> bool:
        return self.initialized and self.last_poll > 0 and time.monotonic() - self.last_poll < 90 and not self.blocked

    def run(self) -> None:
        delay = 1
        while not self.stop.is_set():
            try:
                if not self.initialized:
                    self.initialize()
                self.poll_once()
                delay = 1
            except Exception:
                # Never log exception text: urllib errors may contain token URLs.
                sys.stderr.write("edge ingress=polling status=retry\n")
                self.stop.wait(delay)
                delay = min(delay * 2, 15)


def _json_object(body: bytes) -> bool:
    if not body or len(body) > MAX_BODY_BYTES:
        return False
    try:
        return isinstance(json.loads(body.decode("utf-8")), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def _valid_menu_request(operation: str, body: bytes) -> bool:
    """Keep the Q1.1 menu control plane immutable at the Edge boundary."""
    if operation not in {"setMyCommands", "setChatMenuButton", "getMyCommands", "getChatMenuButton"}:
        return True
    payload = json.loads(body.decode("utf-8"))
    expected = {
        "setMyCommands": {"commands": _MENU_COMMANDS},
        "setChatMenuButton": {"menu_button": _MENU_BUTTON},
        "getMyCommands": {},
        "getChatMenuButton": {},
    }[operation]
    return payload == expected


def make_handler(service: EdgeService) -> type[BaseHTTPRequestHandler]:
    class EdgeHandler(BaseHTTPRequestHandler):
        server_version = "AIMyTimeTelegramEdge/1"

        def log_message(self, fmt: str, *args: object) -> None:
            # No body, token, Telegram user identifier, or Core response is logged.
            sys.stderr.write(f"edge method={self.command} path={self.path.split('?', 1)[0]} status={getattr(self, '_status', 0)} latency_ms={getattr(self, '_latency_ms', 0)} request_id={getattr(self, '_request_id', '-')!s}\n")

        def do_GET(self) -> None:
            self._begin()
            if self.path == "/healthz":
                ingress = service.ingress
                healthy = ingress is None or ingress.healthy()
                self._respond(HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE,
                    {"status": "ok" if healthy else "degraded", "service": "aimytime-telegram-edge",
                     "update_mode": service._config.update_mode,
                     "accepted_updates": ingress.accepted if ingress else None})
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
    service = EdgeService(config)
    server = ThreadingHTTPServer((host, port), make_handler(service))
    if config.update_mode == "polling":
        service.ingress = PollingIngress(service)
        threading.Thread(target=service.ingress.run, name="telegram-ingress", daemon=True).start()
    server.serve_forever()


app = EdgeService  # Allows the service contract to identify this module without a framework dependency.

if __name__ == "__main__":
    main()
