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
from app.services.radar_alert_delivery import RadarAlertDelivery

_MAX_CALLBACK_BYTES = 64
_MENU_COMMANDS = [{"command": "menu", "description": "Открыть доступные действия"}]
_MENU_BUTTON = {"type": "commands"}


class TelegramDeliveryError(RuntimeError):
    """A retryable provider delivery failure without leaking token or payload."""


def telegram_send_payload(message: OutboundDelivery) -> dict[str, object]:
    if message.channel != "telegram_lead":
        raise TelegramDeliveryError("unsupported outbound channel")
    if not message.recipient_id or not message.recipient_id.isdecimal():
        raise TelegramDeliveryError("missing Telegram recipient")
    # Campaigns retain their own durable kind so the worker can re-check the
    # content subscription. They render through the same Telegram sendMessage
    # contract as an ordinary lead-bot message.
    if message.payload.get("kind") not in {"message", "content_campaign"}:
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


def telegram_ops_send_payload(message: OutboundDelivery, *, chat_id: str) -> dict[str, object]:
    """Render a private operations notification for its fixed configured chat."""
    if message.channel != "telegram_ops":
        raise TelegramDeliveryError("unsupported outbound channel")
    if not chat_id.startswith("-") or not chat_id[1:].isdecimal():
        raise TelegramDeliveryError("invalid Telegram ops chat")
    if message.payload.get("kind") != "message":
        raise TelegramDeliveryError("unsupported Telegram payload kind")
    text = message.payload.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise TelegramDeliveryError("invalid Telegram message text")
    return {"chat_id": chat_id, "text": text}


def telegram_radar_alert_payload(message: RadarAlertDelivery) -> dict[str, object]:
    """Render an isolated Radar alert without Lead Bot semantics."""
    if message.payload.get("kind") != "radar_signal" or message.chat_id == 0:
        raise TelegramDeliveryError("invalid Radar alert")
    text = message.payload.get("text")
    source_label = message.payload.get("source_label") or message.payload.get("source_id")
    detected_at = message.payload.get("detected_at")
    published_at = message.payload.get("published_at")
    message_url = message.payload.get("message_url")
    profile_name = message.payload.get("profile_name")
    reason = message.payload.get("reason")
    if (
        not isinstance(text, str)
        or not text.strip()
        or not isinstance(source_label, str)
        or not source_label.strip()
        or not isinstance(detected_at, str)
    ):
        raise TelegramDeliveryError("invalid Radar alert payload")
    when = published_at if isinstance(published_at, str) and published_at else detected_at
    lines = [
        "Радар спроса",
        "",
        text.strip(),
        "",
        f"Источник: {source_label}",
        f"Время: {when}",
    ]
    if isinstance(message_url, str) and message_url.startswith("https://"):
        lines.append(f"Сообщение: {message_url}")
    if isinstance(profile_name, str) and profile_name.strip():
        lines.append(f"Профиль: {profile_name.strip()}")
    if isinstance(reason, str) and reason.strip():
        lines.append(f"Причина: {reason.strip()}")
    rendered = "\n".join(lines)
    if len(rendered) > 4096:
        raise TelegramDeliveryError("Radar alert text too long")
    return {"chat_id": str(message.chat_id), "text": rendered}


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
    # Edge may deliver to Telegram before answering Core. A short read timeout
    # causes outbox retries and duplicate user-visible messages.
    connection = http.client.HTTPSConnection(
        parsed.hostname, parsed.port or 443, timeout=45, context=ssl.create_default_context()
    )
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


class TelegramOpsTransport:
    """Direct, fixed-destination transport for the private operations chat."""

    def __init__(self, *, token: str, chat_id: str, sender: HttpSender = _send_json) -> None:
        if not token.strip() or not chat_id.strip():
            raise ValueError("Telegram ops configuration is required")
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id
        self._sender = sender

    async def deliver(self, message: OutboundDelivery) -> None:
        body = json.dumps(
            telegram_ops_send_payload(message, chat_id=self._chat_id), ensure_ascii=False
        ).encode("utf-8")
        response = await asyncio.to_thread(self._sender, self._url, body)
        if response.get("ok") is not True:
            raise TelegramDeliveryError("Telegram API rejected operations notification")


class TelegramRadarAlertTransport:
    """One configured Radar Bot per binding key; never falls back to Lead Bot."""

    def __init__(self, *, tokens: Mapping[str, str], sender: HttpSender = _send_json) -> None:
        self._urls = {
            key: f"https://api.telegram.org/bot{token}/sendMessage"
            for key, token in tokens.items()
            if isinstance(key, str) and isinstance(token, str) and key.strip() and token.strip()
        }
        if not self._urls:
            raise ValueError("at least one Radar Bot token is required")
        self._sender = sender

    async def deliver(self, message: RadarAlertDelivery) -> None:
        url = self._urls.get(message.bot_binding_key)
        if url is None:
            raise TelegramDeliveryError("Radar Bot binding is not configured")
        body = json.dumps(telegram_radar_alert_payload(message), ensure_ascii=False).encode("utf-8")
        response = await asyncio.to_thread(self._sender, url, body)
        if response.get("ok") is not True:
            raise TelegramDeliveryError("Telegram API rejected Radar alert")


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
