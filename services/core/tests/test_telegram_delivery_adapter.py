import asyncio
import json
import uuid

import pytest

from app.adapters import telegram_delivery
from app.adapters.telegram_delivery import TelegramBotTransport, TelegramDeliveryError, telegram_send_payload
from app.services.outbox_delivery import OutboundDelivery


def _delivery(*, recipient_id: str | None = "900001") -> OutboundDelivery:
    return OutboundDelivery(
        message_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        channel="telegram_lead",
        recipient_id=recipient_id,
        payload={
            "kind": "message",
            "text": "Чем занимается ваш бизнес?",
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
