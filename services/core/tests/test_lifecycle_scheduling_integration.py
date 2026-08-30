from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import ConsultationRequest, DiagnosticReport, DiagnosticSession, OutboundMessage, ScheduledEvent, User
from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.services.consultation_lifecycle import ConsultationLifecycleService
from app.services.scheduled_events import ScheduledEventService
from app.core.timezones import format_moscow


def _url() -> str: return os.environ.get("AI_MY_TIME_TEST_DATABASE_URL", "postgresql+asyncpg:///ai_my_time_test")


async def _clean() -> None:
    factory = create_session_factory(_url())
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE scheduled_events, outbound_messages, attention_items, consultation_requests, diagnostic_reports, diagnostic_sessions, users RESTART IDENTITY CASCADE"))
    finally: await factory.kw["bind"].dispose()


def test_appointment_lifecycle_schedule_and_idempotency() -> None:
    asyncio.run(_clean())
    asyncio.run(_run_lifecycle())
    asyncio.run(_clean())


async def _run_lifecycle() -> None:
    factory = create_session_factory(_url())
    try:
        async with session_scope(factory) as session:
            user = User(lifecycle_stage="consultation_requested"); session.add(user); await session.flush()
            diagnostic = DiagnosticSession(user_id=user.id, status="diagnostic_completed", input_snapshot_json={}); session.add(diagnostic); await session.flush()
            request = ConsultationRequest(user_id=user.id, diagnostic_session_id=diagnostic.id, status="new"); session.add(request); await session.flush()
            lifecycle = ConsultationLifecycleService(session)
            appointment = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
            await lifecycle.schedule_appointment(request, appointment_at=appointment)
            assert request.status == "scheduled" and request.confirmation_state == "pending"
            notice = await session.scalar(select(OutboundMessage).where(OutboundMessage.dedupe_key.like(f"appointment:{request.id}%notice")))
            assert notice is not None
            assert format_moscow(appointment) == "01.09.2026 12:00 МСК"
            assert "01.09.2026 12:00 МСК" in str(notice.payload_json["text"])
            events = list((await session.scalars(select(ScheduledEvent).where(ScheduledEvent.consultation_request_id == request.id))).all())
            assert {event.event_type for event in events} == {"appointment_t24", "appointment_t1", "appointment_auto_cancel"}
            assert len((await session.scalars(select(OutboundMessage))).all()) == 1
            await lifecycle.confirm(request, source="client")
            assert request.confirmation_source == "client"
            await lifecycle.confirm(request, source="client")
            assert len((await session.scalars(select(OutboundMessage))).all()) == 2
            await lifecycle.complete(request, status="completed")
            await lifecycle.complete(request, status="completed")
            messages = list((await session.scalars(select(OutboundMessage))).all())
            assert len([m for m in messages if m.dedupe_key.endswith("thank-you")]) == 1
            assert request.status == "completed"
            assert user.lifecycle_stage == "consultation_completed"
            assert user.communication_status == "subscribed"
    finally: await factory.kw["bind"].dispose()


def test_followup_is_rescheduled_once_and_cancelled() -> None:
    asyncio.run(_clean())
    asyncio.run(_run_followup())
    asyncio.run(_clean())


def test_saved_result_replay_and_repeat_task_create_a_distinct_admin_request() -> None:
    asyncio.run(_clean())
    asyncio.run(_run_saved_result_and_repeat())
    asyncio.run(_clean())


async def _run_saved_result_and_repeat() -> None:
    factory = create_session_factory(_url())
    try:
        async with session_scope(factory) as session:
            user = User(lifecycle_stage="diagnostic_ready"); session.add(user); await session.flush()
            diagnostic = DiagnosticSession(user_id=user.id, status="diagnostic_completed", input_snapshot_json={}); session.add(diagnostic); await session.flush()
            result = DiagnosticResultV2.model_validate({
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
            })
            session.add(DiagnosticReport(
                diagnostic_session_id=diagnostic.id,
                summary=result.client_view.what_is_happening,
                priorities_json=[], next_steps_json=[], limitations_json=[], role_split_json={},
                result_version="v2", result_json=result.model_dump(mode="json"),
            ))
            await session.flush()
            session.add(ConsultationRequest(
                user_id=user.id,
                diagnostic_session_id=diagnostic.id,
                status="completed",
                origin_type="primary_diagnostic",
            ))
            await session.flush()
            lifecycle = ConsultationLifecycleService(session)
            assert await lifecycle.replay_result(user_id=user.id, diagnostic_id=diagnostic.id)
            replay = await session.scalar(select(OutboundMessage.payload_json).where(OutboundMessage.dedupe_key == f"diagnostic:{diagnostic.id}:result-replay"))
            assert replay is not None
            for section in ("Что сейчас происходит", "Где теряется результат", "Как это может работать", "Что может взять на себя система", "Что останется человеку", "Что ещё важно понять"):
                assert section in str(replay["text"])
            repeat = await lifecycle.create_repeat(user_id=user.id, diagnostic_id=diagnostic.id, text="Нужно наладить передачу заявок")
            assert repeat is not None
            assert repeat.origin_type == "repeat_task"
            assert repeat.repeat_task_text == "Нужно наладить передачу заявок"
            assert await session.scalar(select(ConsultationRequest).where(ConsultationRequest.id == repeat.id)) is repeat
            assert len((await session.scalars(select(ConsultationRequest).where(ConsultationRequest.diagnostic_session_id == diagnostic.id))).all()) == 2
    finally:
        await factory.kw["bind"].dispose()


async def _run_followup() -> None:
    factory = create_session_factory(_url())
    try:
        async with session_scope(factory) as session:
            user = User(lifecycle_stage="diagnostic_in_progress"); session.add(user); await session.flush()
            diagnostic = DiagnosticSession(user_id=user.id, status="diagnostic_active", input_snapshot_json={}); session.add(diagnostic); await session.flush()
            scheduler = ScheduledEventService(session)
            first = datetime.now(timezone.utc) + timedelta(hours=24)
            await scheduler.touch_followup(user_id=user.id, diagnostic_id=diagnostic.id, due_at=first)
            await scheduler.touch_followup(user_id=user.id, diagnostic_id=diagnostic.id, due_at=first + timedelta(minutes=1))
            row = await session.scalar(select(ScheduledEvent).where(ScheduledEvent.diagnostic_session_id == diagnostic.id))
            assert row is not None and row.due_at == first + timedelta(minutes=1)
            await scheduler.cancel_followup(diagnostic.id)
            assert row.status == "cancelled"
    finally: await factory.kw["bind"].dispose()
