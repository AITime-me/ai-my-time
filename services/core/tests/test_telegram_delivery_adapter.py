import asyncio
import json
import uuid

import pytest

from app.adapters import telegram_delivery
from app.adapters.telegram_delivery import (
    TelegramBotTransport,
    TelegramCallbackAcknowledger,
    TelegramEdgeCallbackAcknowledger,
    TelegramEdgeTransport,
    TelegramDeliveryError,
    telegram_send_payload,
)
from app.services.outbox_delivery import OutboundDelivery


def _delivery(*, recipient_id: str | None = "900001") -> OutboundDelivery:
    return OutboundDelivery(
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        channel="telegram_lead",
        recipient_id=recipient_id,
        payload={
            "kind": "message",
            "text": "Что является основой вашего бизнеса?",
            "buttons": [{"text": "Услуги", "callback_data": "profile:business_type:Услуги"}],
        },
        lease_token=uuid.uuid4(),
    )


def test_telegram_payload_has_numeric_recipient_and_inline_keyboard() -> None:
    payload = telegram_send_payload(_delivery())
    assert payload["chat_id"] == "900001"
    assert payload["reply_markup"] == {
        "inline_keyboard": [[{"text": "Услуги", "callback_data": "profile:business_type:Услуги"}]]
    }


def test_telegram_payload_rejects_missing_recipient() -> None:
    with pytest.raises(TelegramDeliveryError, match="recipient"):
        telegram_send_payload(_delivery(recipient_id=None))


def test_transport_sends_only_serialized_message_payload() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def sender(url: str, body: bytes) -> dict[str, object]:
        calls.append((url, json.loads(body)))
        return {"ok": True, "result": {"message_id": 1}}

    asyncio.run(TelegramBotTransport(token="test-token", sender=sender).deliver(_delivery()))
    assert len(calls) == 1
    assert calls[0][0].endswith("/sendMessage")
    assert calls[0][1]["chat_id"] == "900001"


def test_callback_acknowledger_sends_immediate_non_business_feedback() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def sender(url: str, body: bytes) -> dict[str, object]:
        calls.append((url, json.loads(body)))
        return {"ok": True, "result": True}

    asyncio.run(TelegramCallbackAcknowledger(token="test-token", sender=sender).acknowledge("callback-1"))
    assert calls == [
        (
            "https://api.telegram.org/bottest-token/answerCallbackQuery",
            {"callback_query_id": "callback-1", "text": "Нажатие получено"},
        )
    ]


def test_edge_transport_uses_only_allowlisted_edge_operation() -> None:
    calls: list[tuple[str, str, str, dict[str, object]]] = []
    def sender(url: str, secret: str, operation: str, body: bytes) -> dict[str, object]:
        calls.append((url, secret, operation, json.loads(body)))
        return {"ok": True}
    asyncio.run(TelegramEdgeTransport(edge_url="https://edge.example", secret="edge-secret", sender=sender).deliver(_delivery()))
    asyncio.run(TelegramEdgeCallbackAcknowledger(edge_url="https://edge.example", secret="edge-secret", sender=sender).acknowledge("callback-1"))
    assert [(row[2], row[3]) for row in calls] == [
        ("sendMessage", telegram_send_payload(_delivery())),
        ("answerCallbackQuery", {"callback_query_id": "callback-1", "text": "Нажатие получено"}),
    ]


def test_telegram_network_connector_resolves_only_ipv6(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_getaddrinfo(host, port, *, family, type):
        seen.update(host=host, port=port, family=family, type=type)
        return []

    monkeypatch.setattr(telegram_delivery.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(OSError, match="no IPv6"):
        telegram_delivery._connect_ipv6(("api.telegram.org", 443))
    assert seen == {
        "host": "api.telegram.org",
        "port": 443,
        "family": telegram_delivery.socket.AF_INET6,
        "type": telegram_delivery.socket.SOCK_STREAM,
    }
