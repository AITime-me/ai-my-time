"""Regression coverage for the closed, owner-bound acceptance restart."""

from __future__ import annotations

import asyncio
import copy
import os
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.models import (
    DiagnosticAcceptanceGrant,
    DiagnosticReport,
    DiagnosticSession,
    DiagnosticTurn,
    LeadBotSession,
    OutboundMessage,
    User,
)
from app.services.diagnostic_acceptance import DiagnosticAcceptanceService
from app.services.lead_profile_flow import PROFILE_STEPS
from tests.doubles import ScriptedDiagnosticProvider


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_closed_acceptance_link_restarts_once_and_preserves_diagnostic_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    owner = 901101
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    try:
        app = create_app()
        app.state.diagnostic_provider_factory = ScriptedDiagnosticProvider
        with TestClient(app) as client:
            assert client.post("/webhooks/telegram/lead", json=_start(1, owner, "qr_conf_main"), headers=headers).status_code == 204
            for version, step in enumerate(PROFILE_STEPS, start=1):
                assert client.post(
                    "/webhooks/telegram/lead",
                    json=_callback(10 + version, owner, f"profile:v2:{version}:{step.code}:0"),
                    headers=headers,
                ).status_code == 204
            # Two replies make the scripted provider persist one v2 report.
            assert client.post("/webhooks/telegram/lead", json=_text(30, owner, "Первое уточнение"), headers=headers).status_code == 204
            assert client.post("/webhooks/telegram/lead", json=_text(31, owner, "Второе уточнение"), headers=headers).status_code == 204

        start_parameter, before = asyncio.run(_issue_and_capture(database_url, owner))
        with TestClient(app) as client:
            assert client.post("/webhooks/telegram/lead", json=_start(40, owner, start_parameter), headers=headers).status_code == 204
            # A used link is a no-op; it cannot make a second run or prompt.
            assert client.post("/webhooks/telegram/lead", json=_start(41, owner, start_parameter), headers=headers).status_code == 204
            # A stale callback from the former completed flow cannot advance it.
            assert client.post(
                "/webhooks/telegram/lead",
                json=_callback(42, owner, "profile:v2:7:business_type:0"),
                headers=headers,
            ).status_code == 204
            # A link presented by a different Telegram identity changes nothing.
            assert client.post("/webhooks/telegram/lead", json=_start(43, 901102, start_parameter), headers=headers).status_code == 204

        asyncio.run(_assert_consumed_restart(database_url, before))
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear(database_url))


async def _issue_and_capture(database_url: str, telegram_user_id: int) -> tuple[str, dict[str, object]]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            flow = await session.scalar(select(LeadBotSession))
            diagnostic = await session.scalar(select(DiagnosticSession))
            report = await session.scalar(select(DiagnosticReport))
            assert flow is not None and diagnostic is not None and report is not None
            turns = int(await session.scalar(select(func.count()).select_from(DiagnosticTurn)) or 0)
            before = {
                "flow": {
                    "id": str(flow.id),
                    "user_id": str(flow.user_id),
                    "state": flow.state,
                    "status": flow.status,
                    "version": flow.version,
                    "flow_version": flow.flow_version,
                },
                "diagnostic_id": str(diagnostic.id),
                "diagnostic_snapshot": copy.deepcopy(diagnostic.input_snapshot_json),
                "report_id": str(report.id),
                "turns": turns,
                "outbox": int(await session.scalar(select(func.count()).select_from(OutboundMessage)) or 0),
                "users": int(await session.scalar(select(func.count()).select_from(User)) or 0),
            }
            issued = await DiagnosticAcceptanceService(session).issue(
                user_id=flow.user_id,
                ttl=timedelta(minutes=30),
            )
            with pytest.raises(ValueError, match="active acceptance"):
                await DiagnosticAcceptanceService(session).issue(user_id=flow.user_id, ttl=timedelta(minutes=30))
            return issued.raw_start_parameter, before
    finally:
        await factory.kw["bind"].dispose()


async def _assert_consumed_restart(database_url: str, before: dict[str, object]) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            flow = await session.scalar(select(LeadBotSession))
            diagnostic = await session.scalar(select(DiagnosticSession))
            report = await session.scalar(select(DiagnosticReport))
            grant = await session.scalar(select(DiagnosticAcceptanceGrant))
            assert flow is not None and diagnostic is not None and report is not None and grant is not None
            assert (flow.flow_version, flow.status, flow.state, flow.version) == ("v2", "open", "business_type", 8)
            assert diagnostic.id == uuid.UUID(before["diagnostic_id"])
            assert diagnostic.input_snapshot_json == before["diagnostic_snapshot"]
            assert str(report.id) == before["report_id"]
            assert int(await session.scalar(select(func.count()).select_from(DiagnosticTurn)) or 0) == before["turns"]
            assert grant.consumed_at is not None
            assert all(
                grant.prior_flow_snapshot_json[key] == value
                for key, value in before["flow"].items()
            )
            assert int(await session.scalar(select(func.count()).select_from(User)) or 0) == before["users"]
            assert int(await session.scalar(select(func.count()).select_from(OutboundMessage)) or 0) == before["outbox"] + 1
            assert await session.scalar(
                select(func.count()).select_from(OutboundMessage).group_by(OutboundMessage.dedupe_key).having(func.count() > 1)
            ) is None
    finally:
        await factory.kw["bind"].dispose()


def _start(update_id: int, telegram_user_id: int, parameter: str) -> dict[str, object]:
    return {"update_id": update_id, "message": {"chat": {"type": "private"}, "from": {"id": telegram_user_id}, "text": f"/start {parameter}"}}


def _text(update_id: int, telegram_user_id: int, value: str) -> dict[str, object]:
    return {"update_id": update_id, "message": {"chat": {"type": "private"}, "from": {"id": telegram_user_id}, "text": value}}


def _callback(update_id: int, telegram_user_id: int, data: str) -> dict[str, object]:
    return {"update_id": update_id, "callback_query": {"id": f"callback-{update_id}", "from": {"id": telegram_user_id}, "message": {"chat": {"type": "private"}}, "data": data}}


async def _clear(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE diagnostic_acceptance_grants, diagnostic_reports, diagnostic_sessions, profile_answers, business_profiles, conference_entries, events, touchpoints, outbound_messages, lead_bot_sessions, user_identities, users RESTART IDENTITY CASCADE"))
    finally:
        await factory.kw["bind"].dispose()
