from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import ConsultationRequest, DiagnosticSession, OutboundMessage, ScheduledEvent, User
from app.services.consultation_lifecycle import ConsultationLifecycleService
from app.services.scheduled_events import ScheduledEventService


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
            appointment = datetime.now(timezone.utc) + timedelta(days=2)
            await lifecycle.schedule_appointment(request, appointment_at=appointment)
            assert request.status == "scheduled" and request.confirmation_state == "pending"
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
            assert user.communication_status == "subscribed"
    finally: await factory.kw["bind"].dispose()


def test_followup_is_rescheduled_once_and_cancelled() -> None:
    asyncio.run(_clean())
    asyncio.run(_run_followup())
    asyncio.run(_clean())


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
