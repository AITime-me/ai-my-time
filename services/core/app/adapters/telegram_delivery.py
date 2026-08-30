"""Narrow Telegram Bot API delivery adapter for durable Lead Bot messages."""

from __future__ import annotations

import asyncio
import http.client
import json
import socket
import ssl
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

from app.services.outbox_delivery import OutboundDelivery

_MAX_CALLBACK_BYTES = 64
_MENU_COMMANDS = [{"command": "menu", "description": "Что можно сделать?"}]
_MENU_BUTTON = {"type": "commands"}


class TelegramDeliveryError(RuntimeError):
    """A retryable provider delivery failure without leaking token or payload."""


def telegram_send_payload(message: OutboundDelivery) -> dict[str, object]:
    if message.channel != "telegram_lead":
        raise TelegramDeliveryError("unsupported outbound channel")
    if not message.recipient_id or not message.recipient_id.isdecimal():
        raise TelegramDeliveryError("missing Telegram recipient")
    if message.payload.get("kind") != "message":
        raise TelegramDeliveryError("unsupported Telegram payload kind")
    text = message.payload.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise TelegramDeliveryError("invalid Telegram message text")
    body: dict[str, object] = {"chat_id": message.recipient_id, "text": text}
    buttons = message.payload.get("buttons", [])
    if not isinstance(buttons, list):
        raise TelegramDeliveryError("invalid Telegram buttons")
    if buttons:
        rows: list[list[dict[str, str]]] = []
        for button in buttons:
            if not isinstance(button, dict):
                raise TelegramDeliveryError("invalid Telegram button")
            label = button.get("text")
            callback_data = button.get("callback_data")
            url = button.get("url")
            if not isinstance(label, str) or not label or (callback_data is None and url is None) or (callback_data is not None and url is not None):
                raise TelegramDeliveryError("invalid Telegram button")
            if callback_data is not None:
                if not isinstance(callback_data, str) or not callback_data or len(callback_data.encode("utf-8")) > _MAX_CALLBACK_BYTES:
                    raise TelegramDeliveryError("invalid Telegram callback data")
                rows.append([{"text": label, "callback_data": callback_data}])
            else:
                if not isinstance(url, str) or not url.startswith("https://"):
                    raise TelegramDeliveryError("invalid Telegram button URL")
                rows.append([{"text": label, "url": url}])
        body["reply_markup"] = {"inline_keyboard": rows}
    return body


HttpSender = Callable[[str, bytes], Mapping[str, Any]]


def _connect_ipv6(address: tuple[str, int], timeout: float | None = None, source_address=None):
    """Open the fixed Telegram API connection through DNS-resolved IPv6 only."""

    host, port = address
    errors: list[OSError] = []
    for family, socktype, protocol, _, sockaddr in socket.getaddrinfo(
        host, port, family=socket.AF_INET6, type=socket.SOCK_STREAM
    ):
        sock = socket.socket(family, socktype, protocol)
        try:
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address is not None:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as error:
            errors.append(error)
            sock.close()
    if errors:
        raise errors[-1]
    raise OSError("Telegram API has no IPv6 address")


def _send_json(url: str, body: bytes) -> Mapping[str, Any]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.telegram.org":
        raise TelegramDeliveryError("unsupported Telegram API URL")
    connection = http.client.HTTPSConnection(
        parsed.hostname, parsed.port or 443, timeout=10, context=ssl.create_default_context()
    )
    connection._create_connection = _connect_ipv6
    try:
        connection.request("POST", parsed.path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        decoded = json.loads(response.read().decode("utf-8"))
    except (http.client.HTTPException, OSError, ssl.SSLError, TimeoutError, json.JSONDecodeError) as error:
        raise TelegramDeliveryError("Telegram API request failed") from error
    finally:
        connection.close()
    if not isinstance(decoded, dict):
        raise TelegramDeliveryError("invalid Telegram API response")
    return decoded


def _send_edge_json(endpoint: str, secret: str, operation: str, body: bytes) -> Mapping[str, Any]:
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path.rstrip("/"):
        raise TelegramDeliveryError("invalid Telegram Edge URL")
    connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=10, context=ssl.create_default_context())
    try:
        connection.request("POST", f"/v1/telegram/{operation}", body=body, headers={"Content-Type": "application/json", "X-Aimytime-Edge-Auth": secret})
        response = connection.getresponse()
        decoded = json.loads(response.read().decode("utf-8"))
    except (http.client.HTTPException, OSError, ssl.SSLError, TimeoutError, json.JSONDecodeError) as error:
        raise TelegramDeliveryError("Telegram Edge request failed") from error
    finally:
        connection.close()
    if not isinstance(decoded, dict):
        raise TelegramDeliveryError("invalid Telegram Edge response")
    return decoded


class TelegramBotTransport:
    """Converts provider-neutral queue payloads into one safe sendMessage call."""

    def __init__(self, *, token: str, sender: HttpSender = _send_json) -> None:
        if not token.strip():
            raise ValueError("Telegram bot token is required")
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._sender = sender

    async def deliver(self, message: OutboundDelivery) -> None:
        body = json.dumps(telegram_send_payload(message), ensure_ascii=False).encode("utf-8")
        response = await asyncio.to_thread(self._sender, self._url, body)
        if response.get("ok") is not True:
            raise TelegramDeliveryError("Telegram API rejected message")


class TelegramCallbackAcknowledger:
    """Closes a Telegram callback spinner without changing business state."""

    def __init__(self, *, token: str, sender: HttpSender = _send_json) -> None:
        if not token.strip():
            raise ValueError("Telegram bot token is required")
        self._url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
        self._sender = sender

    async def acknowledge(self, callback_query_id: str) -> None:
        if not callback_query_id or len(callback_query_id) > 128:
            raise TelegramDeliveryError("invalid Telegram callback query")
        payload: dict[str, str] = {"callback_query_id": callback_query_id, "text": "Нажатие получено"}
        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
        response = await asyncio.to_thread(self._sender, self._url, body)
        if response.get("ok") is not True:
            raise TelegramDeliveryError("Telegram API rejected callback acknowledgement")


class TelegramEdgeTransport:
    """Core-side adapter: durable outbox remains authoritative; Edge has no queue."""
    def __init__(self, *, edge_url: str, secret: str, sender: Callable[[str, str, str, bytes], Mapping[str, Any]] = _send_edge_json) -> None:
        if not edge_url.strip() or not secret.strip(): raise ValueError("Telegram Edge configuration is required")
        self._edge_url, self._secret, self._sender = edge_url, secret, sender

    async def deliver(self, message: OutboundDelivery) -> None:
        body = json.dumps(telegram_send_payload(message), ensure_ascii=False).encode("utf-8")
        response = await asyncio.to_thread(self._sender, self._edge_url, self._secret, "sendMessage", body)
        if response.get("ok") is not True: raise TelegramDeliveryError("Telegram Edge rejected message")


class TelegramEdgeCallbackAcknowledger:
    def __init__(self, *, edge_url: str, secret: str, sender: Callable[[str, str, str, bytes], Mapping[str, Any]] = _send_edge_json) -> None:
        if not edge_url.strip() or not secret.strip(): raise ValueError("Telegram Edge configuration is required")
        self._edge_url, self._secret, self._sender = edge_url, secret, sender

    async def acknowledge(self, callback_query_id: str) -> None:
        if not callback_query_id or len(callback_query_id) > 128: raise TelegramDeliveryError("invalid Telegram callback query")
        payload: dict[str, str] = {"callback_query_id": callback_query_id, "text": "Нажатие получено"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response = await asyncio.to_thread(self._sender, self._edge_url, self._secret, "answerCallbackQuery", body)
        if response.get("ok") is not True: raise TelegramDeliveryError("Telegram Edge rejected callback acknowledgement")


class TelegramEdgeMenuConfigurer:
    """Configure and verify the one fixed native Telegram commands-menu item."""

    def __init__(self, *, edge_url: str, secret: str, sender: Callable[[str, str, str, bytes], Mapping[str, Any]] = _send_edge_json) -> None:
        if not edge_url.strip() or not secret.strip():
            raise ValueError("Telegram Edge configuration is required")
        self._edge_url, self._secret, self._sender = edge_url, secret, sender

    async def configure_and_verify(self) -> None:
        for operation, payload in (
            ("setMyCommands", {"commands": _MENU_COMMANDS}),
            ("setChatMenuButton", {"menu_button": _MENU_BUTTON}),
            ("getMyCommands", {}),
            ("getChatMenuButton", {}),
        ):
            response = await asyncio.to_thread(
                self._sender,
                self._edge_url,
                self._secret,
                operation,
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            )
            if response.get("ok") is not True:
                raise TelegramDeliveryError("Telegram Edge rejected commands-menu configuration")
