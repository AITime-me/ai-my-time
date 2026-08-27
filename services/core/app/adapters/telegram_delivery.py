"""Narrow Telegram Bot API delivery adapter for durable Lead Bot messages."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.outbox_delivery import OutboundDelivery

_MAX_CALLBACK_BYTES = 64


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
            if not isinstance(label, str) or not label or not isinstance(callback_data, str):
                raise TelegramDeliveryError("invalid Telegram button")
            if not callback_data or len(callback_data.encode("utf-8")) > _MAX_CALLBACK_BYTES:
                raise TelegramDeliveryError("invalid Telegram callback data")
            rows.append([{"text": label, "callback_data": callback_data}])
        body["reply_markup"] = {"inline_keyboard": rows}
    return body


HttpSender = Callable[[str, bytes], Mapping[str, Any]]


def _send_json(url: str, body: bytes) -> Mapping[str, Any]:
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed Telegram URL from config
            decoded = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise TelegramDeliveryError("Telegram API request failed") from error
    if not isinstance(decoded, dict):
        raise TelegramDeliveryError("invalid Telegram API response")
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
