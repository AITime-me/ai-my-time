"""Real PostgreSQL proof of the narrow secret-checked Telegram /start ingress."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.models import DiagnosticSession, DiagnosticTurn, Event, LeadBotSession, OutboundMessage, ProfileAnswer
from app.services.lead_profile_flow import PROFILE_STEPS
from tests.doubles import ScriptedDiagnosticProvider


class FailingDiagnosticProvider:
    async def advance(self, _diagnostic_input):
        raise RuntimeError("provider unavailable")


class RecordingCallbackAcknowledger:
    def __init__(self) -> None:
        self.callback_ids: list[str] = []

    async def acknowledge(self, callback_query_id: str) -> None:
        self.callback_ids.append(callback_query_id)


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_private_start_is_secret_checked_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    payload = {
        "update_id": 1001,
        "message": {
            "chat": {"type": "private"},
            "from": {"id": 901001},
            "text": "/start qr_conf_main",
        },
    }
    try:
        with TestClient(create_app()) as client:
            assert client.post("/webhooks/telegram/lead", json=payload).status_code == 401
            headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
            assert client.post("/webhooks/telegram/lead", json=payload, headers=headers).status_code == 204
            assert client.post("/webhooks/telegram/lead", json=payload, headers=headers).status_code == 204
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


def test_unrelated_or_malformed_telegram_payload_is_acknowledged_without_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    try:
        with TestClient(create_app()) as client:
            assert client.post(
                "/webhooks/telegram/lead", json={"message": {"chat": {}}}, headers=headers
            ).status_code == 204
            assert client.post(
                "/webhooks/telegram/lead", json={"edited_message": {}}, headers=headers
            ).status_code == 204
        assert asyncio.run(_flow_counts(database_url)) == (None, 0, 0)
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


def test_profile_callbacks_advance_only_the_expected_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    telegram_user_id = 901002
    start_payload = {
        "update_id": 1002,
        "message": {
            "chat": {"type": "private"},
            "from": {"id": telegram_user_id},
            "text": "/start qr_conf_main",
        },
    }
    try:
        app = create_app()
        app.state.diagnostic_provider_factory = ScriptedDiagnosticProvider
        with TestClient(app) as client:
            assert client.post("/webhooks/telegram/lead", json=start_payload, headers=headers).status_code == 204
            invalid = _callback_payload(
                update_id=1003,
                telegram_user_id=telegram_user_id,
                data="profile:team_size:1–3",
            )
            assert client.post("/webhooks/telegram/lead", json=invalid, headers=headers).status_code == 204
            for version, (index, step) in enumerate(enumerate(PROFILE_STEPS, start=1004), start=1):
                payload = _callback_payload(
                    update_id=index,
                    telegram_user_id=telegram_user_id,
                    data=f"profile:v2:{version}:{step.code}:0",
                )
                assert client.post("/webhooks/telegram/lead", json=payload, headers=headers).status_code == 204
        assert asyncio.run(_flow_counts(database_url)) == ("completed", 7, 1)
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


def test_callback_is_acknowledged_immediately_and_cta_keeps_static_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    telegram_user_id = 901004
    acknowledger = RecordingCallbackAcknowledger()
    try:
        app = create_app()
        app.state.diagnostic_provider_factory = ScriptedDiagnosticProvider
        app.state.telegram_callback_acknowledger_factory = lambda: acknowledger
        with TestClient(app) as client:
            assert client.post(
                "/webhooks/telegram/lead",
                json={
                    "update_id": 1300,
                    "message": {
                        "chat": {"type": "private"},
                        "from": {"id": telegram_user_id},
                        "text": "/start qr_conf_main",
                    },
                },
                headers=headers,
            ).status_code == 204
            for version, step in enumerate(PROFILE_STEPS, start=1):
                assert client.post(
                    "/webhooks/telegram/lead",
                    json=_callback_payload(
                        update_id=1300 + version,
                        telegram_user_id=telegram_user_id,
                        data=f"profile:v2:{version}:{step.code}:0",
                    ),
                    headers=headers,
                ).status_code == 204
            assert client.post(
                "/webhooks/telegram/lead",
                json={
                    "update_id": 1400,
                    "message": {
                        "chat": {"type": "private"},
                        "from": {"id": telegram_user_id},
                        "text": "Первое уточнение",
                    },
                },
                headers=headers,
            ).status_code == 204
            assert client.post(
                "/webhooks/telegram/lead",
                json={
                    "update_id": 1401,
                    "message": {
                        "chat": {"type": "private"},
                        "from": {"id": telegram_user_id},
                        "text": "Второе уточнение",
                    },
                },
                headers=headers,
            ).status_code == 204
            diagnostic_id = asyncio.run(_completed_diagnostic_id(database_url))
            assert client.post(
                "/webhooks/telegram/lead",
                json=_callback_payload(
                    update_id=1500,
                    telegram_user_id=telegram_user_id,
                    data=f"diagnostic:consult:{diagnostic_id}",
                ),
                headers=headers,
            ).status_code == 204
        assert acknowledger.callback_ids[-1] == "callback-1500"
        assert asyncio.run(_cta_counts(database_url, diagnostic_id)) == (1, 1, True)
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


@pytest.mark.parametrize("provider_factory", [None, FailingDiagnosticProvider])
def test_cards_persist_and_fallback_stays_recoverable_without_a_provider(
    monkeypatch: pytest.MonkeyPatch, provider_factory
) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    telegram_user_id = 901003
    try:
        app = create_app()
        if provider_factory is not None:
            app.state.diagnostic_provider_factory = provider_factory
        with TestClient(app) as client:
            assert client.post("/webhooks/telegram/lead", json={
                "update_id": 1100, "message": {"chat": {"type": "private"}, "from": {"id": telegram_user_id}, "text": "/start qr_conf_main"},
            }, headers=headers).status_code == 204
            for version, (index, step) in enumerate(enumerate(PROFILE_STEPS, start=1101), start=1):
                assert client.post("/webhooks/telegram/lead", json=_callback_payload(
                    update_id=index, telegram_user_id=telegram_user_id, data=f"profile:v2:{version}:{step.code}:0"
                ), headers=headers).status_code == 204
            assert client.post("/webhooks/telegram/lead", json={
                "update_id": 1199, "message": {"chat": {"type": "private"}, "from": {"id": telegram_user_id}, "text": "/start qr_conf_main"},
            }, headers=headers).status_code == 204
            assert client.post("/webhooks/telegram/lead", json={
                "update_id": 1200, "message": {"chat": {"type": "private"}, "from": {"id": telegram_user_id}, "text": "Продолжим?"},
            }, headers=headers).status_code == 204
        assert asyncio.run(_fallback_state(database_url)) == ("completed", "prepared", 6, 0, 7, 1)
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


def _callback_payload(*, update_id: int, telegram_user_id: int, data: str) -> dict[str, object]:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"callback-{update_id}",
            "from": {"id": telegram_user_id},
            "message": {"chat": {"type": "private"}},
            "data": data,
        },
    }


async def _flow_counts(database_url: str) -> tuple[str | None, int, int]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            flow = await session.scalar(select(LeadBotSession))
            if flow is None:
                return (
                    None,
                    await session.scalar(select(func.count()).select_from(OutboundMessage)),
                    await session.scalar(select(func.count()).select_from(DiagnosticSession)),
                )
            return (
                flow.status,
                await session.scalar(select(func.count()).select_from(OutboundMessage)),
                await session.scalar(select(func.count()).select_from(DiagnosticSession)),
            )
    finally:
        await factory.kw["bind"].dispose()


async def _completed_diagnostic_id(database_url: str) -> str:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            diagnostic = await session.scalar(
                select(DiagnosticSession)
                .where(DiagnosticSession.status == "diagnostic_completed")
                .order_by(DiagnosticSession.created_at.desc())
            )
            assert diagnostic is not None
            return str(diagnostic.id)
    finally:
        await factory.kw["bind"].dispose()


async def _cta_counts(database_url: str, diagnostic_id: str) -> tuple[int, int, bool]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            events = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Event)
                    .where(Event.kind == "consultation_requested")
                )
                or 0
            )
            confirmations = int(
                await session.scalar(
                    select(func.count())
                    .select_from(OutboundMessage)
                    .where(OutboundMessage.dedupe_key == f"diagnostic:{diagnostic_id}:consultation:confirmation")
                )
                or 0
            )
            confirmation = await session.scalar(
                select(OutboundMessage.payload_json).where(
                    OutboundMessage.dedupe_key == f"diagnostic:{diagnostic_id}:consultation:confirmation"
                )
            )
            return events, confirmations, bool(
                confirmation
                and "Повторно нажимать кнопку не нужно" in str(confirmation.get("text"))
                and not confirmation.get("buttons")
            )
    finally:
        await factory.kw["bind"].dispose()


async def _fallback_state(database_url: str) -> tuple[str | None, str | None, int, int, int, int]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            flow = await session.scalar(select(LeadBotSession))
            diagnostic = await session.scalar(select(DiagnosticSession))
            return (
                flow.status if flow else None,
                diagnostic.status if diagnostic else None,
                int(await session.scalar(select(func.count()).select_from(ProfileAnswer)) or 0),
                int(await session.scalar(select(func.count()).select_from(DiagnosticTurn)) or 0),
                int(await session.scalar(select(func.count()).select_from(OutboundMessage)) or 0),
                int(await session.scalar(select(func.count()).select_from(OutboundMessage).where(OutboundMessage.dedupe_key.like("%provider-unavailable"))) or 0),
            )
    finally:
        await factory.kw["bind"].dispose()


async def _clear_conference_tables(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE diagnostic_reports, diagnostic_sessions, profile_answers, "
                    "business_profiles, conference_entries, events, touchpoints, "
                    "user_identities, users RESTART IDENTITY CASCADE"
                )
            )
    finally:
        await factory.kw["bind"].dispose()
