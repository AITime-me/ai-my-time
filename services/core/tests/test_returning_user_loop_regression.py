"""Regression for the production returning-user Telegram loop.

Scenario: completed diagnostic → website radar start → new task → stop.
Worker cycles must not enqueue duplicate semantic lead messages.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import func, select
from starlette.testclient import TestClient

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.models import (
    ConsultationRequest,
    DiagnosticReport,
    DiagnosticSession,
    OutboundMessage,
    Touchpoint,
    User,
    UserIdentity,
)
from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.schemas.website import WebsiteStartCommand
from app.services.outbox_delivery import OutboundWorker
from app.services.website_intake import WebsiteIntakeService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


class _RecordingTransport:
    def __init__(self) -> None:
        self.deliveries: list[object] = []

    async def deliver(self, message) -> None:
        self.deliveries.append(message)


def test_returning_website_radar_new_task_does_not_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
    telegram_user_id = 99088001
    diagnostic_id = asyncio.run(_seed_completed_user(database_url, telegram_user_id))
    transport = _RecordingTransport()
    try:
        with TestClient(create_app()) as client:
            # Website deep-link with radar intent.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_start_payload(9001, telegram_user_id, "site_consultant_radar"),
                    headers=headers,
                ).status_code
                == 204
            )
            # Redeliver /start — bridge must stay single.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_start_payload(9002, telegram_user_id, "site_consultant_radar"),
                    headers=headers,
                ).status_code
                == 204
            )
            # Choose new task.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_callback_payload(
                        9003, telegram_user_id, f"diagnostic:repeat:{diagnostic_id}"
                    ),
                    headers=headers,
                ).status_code
                == 204
            )
            # Same callback redelivery.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_callback_payload(
                        9003, telegram_user_id, f"diagnostic:repeat:{diagnostic_id}"
                    ),
                    headers=headers,
                ).status_code
                == 204
            )
            # User describes the new radar task.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_text_payload(9004, telegram_user_id, "интересует радар спроса"),
                    headers=headers,
                ).status_code
                == 204
            )
            # Stray follow-up text must not reopen diagnostic CTA/result.
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_text_payload(9005, telegram_user_id, "ещё раз про радар"),
                    headers=headers,
                ).status_code
                == 204
            )
            # Explicit re-submit attempt while active → one already-accepted.
            asyncio.run(_force_repeat_stage(database_url, diagnostic_id))
            assert (
                client.post(
                    "/webhooks/telegram/lead",
                    json=_text_payload(9006, telegram_user_id, "интересует радар спроса"),
                    headers=headers,
                ).status_code
                == 204
            )

        # Multiple worker cycles must not invent new semantic lead messages.
        asyncio.run(_drain_worker(database_url, transport, cycles=5))
        counts = asyncio.run(_outbound_counts(database_url, diagnostic_id))
        assert counts["bridge"] == 1
        assert counts["repeat_prompt"] == 1
        assert counts["task_confirmation"] == 1
        assert counts["already_accepted"] == 1
        assert counts["primary_ready"] == 0
        assert counts["completed_info"] == 0
        assert counts["consultations"] == 1
        assert counts["ops_consultation"] == 1
        assert "Радар спроса" in counts["ops_text"]
        assert counts["touchpoint_intent"] == "radar"
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear(database_url))


async def _seed_completed_user(database_url: str, telegram_user_id: int) -> str:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            user = User(lifecycle_stage="diagnostic_ready", display_name="Loop Regression")
            session.add(user)
            await session.flush()
            session.add(
                UserIdentity(
                    user_id=user.id,
                    provider="telegram",
                    connection_scope="ai_my_time_lead_bot",
                    external_id=str(telegram_user_id),
                )
            )
            diagnostic = DiagnosticSession(
                user_id=user.id,
                status="diagnostic_completed",
                input_snapshot_json={},
            )
            session.add(diagnostic)
            await session.flush()
            result = DiagnosticResultV2.model_validate(
                {
                    "contract_version": "v2",
                    "evidence": {"facts": ["Заявки фиксируются вручную"]},
                    "mechanism": "Нет единого следующего шага.",
                    "problem_types": ["execution_gap"],
                    "problem_scale": "process",
                    "solution_class_id": "lead_intake_contour",
                    "client_view": {
                        "what_is_happening": "Заявки ведутся вручную.",
                        "where_result_is_lost": "Следующий шаг теряется.",
                        "future_process": "Система фиксирует следующий шаг.",
                        "system_responsibilities": ["Фиксировать следующий шаг"],
                        "human_responsibilities": ["Вести нестандартные переговоры"],
                        "open_questions": ["Уточнить роли"],
                    },
                }
            )
            session.add(
                DiagnosticReport(
                    diagnostic_session_id=diagnostic.id,
                    summary=result.client_view.what_is_happening,
                    priorities_json=[],
                    next_steps_json=[],
                    limitations_json=[],
                    role_split_json={},
                    result_version="v2",
                    result_json=result.model_dump(mode="json"),
                )
            )
            return str(diagnostic.id)
    finally:
        await factory.kw["bind"].dispose()


async def _drain_worker(database_url: str, transport: _RecordingTransport, *, cycles: int) -> None:
    factory = create_session_factory(database_url)
    worker = OutboundWorker(factory, transport)
    try:
        for _ in range(cycles):
            await worker.run_once(limit=50)
    finally:
        await factory.kw["bind"].dispose()


async def _force_repeat_stage(database_url: str, diagnostic_id: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            user = await session.scalar(select(User))
            assert user is not None
            user.lifecycle_stage = f"repeat_task_input:{diagnostic_id}"
    finally:
        await factory.kw["bind"].dispose()


async def _outbound_counts(database_url: str, diagnostic_id: str) -> dict[str, object]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            rows = list((await session.scalars(select(OutboundMessage))).all())
            texts = [str((r.payload_json or {}).get("text") or "") for r in rows]
            keys = [r.dedupe_key or "" for r in rows]
            ops = next((r for r in rows if (r.dedupe_key or "").startswith("ops:consultation-created:")), None)
            touchpoint = await session.scalar(
                select(Touchpoint).order_by(Touchpoint.observed_at.desc()).limit(1)
            )
            intent = None
            if touchpoint and isinstance(touchpoint.metadata_json, dict):
                intent = touchpoint.metadata_json.get("intent")
            return {
                "bridge": sum(1 for k in keys if k == f"diagnostic:{diagnostic_id}:bridge"),
                "repeat_prompt": sum(
                    1 for k in keys if k == f"diagnostic:{diagnostic_id}:repeat-prompt"
                ),
                "task_confirmation": sum(
                    1 for t in texts if t.startswith("Задача получена.")
                ),
                "already_accepted": sum(
                    1 for k in keys if k.endswith(":already-accepted")
                ),
                "primary_ready": sum(1 for t in texts if "Первичный разбор готов" in t),
                "completed_info": sum(
                    1 for k in keys if k.endswith(":completed:info")
                ),
                "consultations": int(
                    await session.scalar(select(func.count()).select_from(ConsultationRequest))
                    or 0
                ),
                "ops_consultation": 1 if ops is not None else 0,
                "ops_text": str((ops.payload_json or {}).get("text") or "") if ops else "",
                "touchpoint_intent": intent,
            }
    finally:
        await factory.kw["bind"].dispose()


async def _clear(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                __import__("sqlalchemy").text("TRUNCATE TABLE users RESTART IDENTITY CASCADE")
            )
    finally:
        await factory.kw["bind"].dispose()


def _start_payload(update_id: int, telegram_user_id: int, entry_code: str) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "chat": {"type": "private", "id": telegram_user_id},
            "from": {"id": telegram_user_id, "first_name": "Loop"},
            "text": f"/start {entry_code}",
        },
    }


def _callback_payload(update_id: int, telegram_user_id: int, data: str) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "from": {"id": telegram_user_id, "first_name": "Loop"},
            "data": data,
            "message": {
                "message_id": update_id,
                "chat": {"type": "private", "id": telegram_user_id},
            },
        },
    }


def _text_payload(update_id: int, telegram_user_id: int, text: str) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "chat": {"type": "private", "id": telegram_user_id},
            "from": {"id": telegram_user_id, "first_name": "Loop"},
            "text": text,
        },
    }
