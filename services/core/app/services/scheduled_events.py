"""Durable business scheduler.  It is deliberately independent from outbox retries."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import session_scope
from app.models import ConsultationRequest, DiagnosticSession, ScheduledEvent, User
from app.core.timezones import format_moscow
from app.services.outbox import OutboundQueue

PENDING = "pending"
PROCESSING = "processing"
FIRED = "fired"
CANCELLED = "cancelled"
FAILED = "failed"


class ScheduledEventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schedule(self, *, user_id: uuid.UUID, event_type: str, due_at: datetime,
                       idempotency_key: str, consultation_request_id: uuid.UUID | None = None,
                       diagnostic_session_id: uuid.UUID | None = None, payload: dict[str, object] | None = None) -> ScheduledEvent:
        if due_at.tzinfo is None:
            raise ValueError("scheduled due_at must be timezone-aware")
        statement = insert(ScheduledEvent).values(
            user_id=user_id, consultation_request_id=consultation_request_id,
            diagnostic_session_id=diagnostic_session_id, event_type=event_type,
            due_at=due_at, payload_json=payload or {}, idempotency_key=idempotency_key, status=PENDING,
        ).on_conflict_do_nothing(index_elements=["idempotency_key"]).returning(ScheduledEvent.id)
        event_id = await self._session.scalar(statement)
        if event_id is None:
            existing = await self._session.scalar(select(ScheduledEvent).where(ScheduledEvent.idempotency_key == idempotency_key))
            assert existing is not None
            if existing.status == PENDING and existing.due_at != due_at:
                existing.due_at = due_at
            return existing
        event = await self._session.get(ScheduledEvent, event_id)
        assert event is not None
        return event

    async def cancel_for_consultation(self, consultation_id: uuid.UUID) -> None:
        await self._session.execute(update(ScheduledEvent).where(
            ScheduledEvent.consultation_request_id == consultation_id,
            ScheduledEvent.status.in_((PENDING, PROCESSING)),
        ).values(status=CANCELLED, lease_token=None, lease_expires_at=None))

    async def cancel_followup(self, diagnostic_id: uuid.UUID) -> None:
        await self._session.execute(update(ScheduledEvent).where(
            ScheduledEvent.diagnostic_session_id == diagnostic_id,
            ScheduledEvent.event_type == "diagnostic_followup",
            ScheduledEvent.status.in_((PENDING, PROCESSING)),
        ).values(status=CANCELLED, lease_token=None, lease_expires_at=None))

    async def touch_followup(self, *, user_id: uuid.UUID, diagnostic_id: uuid.UUID, due_at: datetime) -> None:
        delivered = await self._session.scalar(select(ScheduledEvent.id).where(
            ScheduledEvent.diagnostic_session_id == diagnostic_id, ScheduledEvent.event_type == "diagnostic_followup",
            ScheduledEvent.status == FIRED,
        ))
        if delivered is None:
            await self.schedule(user_id=user_id, diagnostic_session_id=diagnostic_id, event_type="diagnostic_followup",
                                due_at=due_at, idempotency_key=f"diagnostic-followup:{diagnostic_id}")

    async def appointment_events(self, request: ConsultationRequest, *, now: datetime | None = None) -> None:
        if request.appointment_at is None:
            raise ValueError("appointment_at required")
        now = now or datetime.now(timezone.utc)
        appointment = request.appointment_at
        await self.cancel_for_consultation(request.id)
        base = f"appointment:{request.id}:{appointment.isoformat()}"
        if appointment - now >= timedelta(hours=24):
            await self.schedule(user_id=request.user_id, consultation_request_id=request.id, event_type="appointment_t24",
                                due_at=appointment - timedelta(hours=24), idempotency_key=f"{base}:t24")
            deadline = appointment - timedelta(hours=12)
        elif appointment - now > timedelta(hours=1):
            deadline = min(now + timedelta(hours=2), appointment - timedelta(hours=1))
        else:
            raise ValueError("appointments under one hour require owner confirmation")
        await self.schedule(user_id=request.user_id, consultation_request_id=request.id, event_type="appointment_t1",
                            due_at=appointment - timedelta(hours=1), idempotency_key=f"{base}:t1")
        if request.confirmation_state != "confirmed":
            await self.schedule(user_id=request.user_id, consultation_request_id=request.id, event_type="appointment_auto_cancel",
                                due_at=deadline, idempotency_key=f"{base}:auto-cancel")

    async def claim_due(self, *, limit: int = 20) -> list[ScheduledEvent]:
        now = datetime.now(timezone.utc)
        await self._session.execute(update(ScheduledEvent).where(
            ScheduledEvent.status == PROCESSING, ScheduledEvent.lease_expires_at < now
        ).values(status=PENDING, lease_token=None, lease_expires_at=None))
        rows = list((await self._session.scalars(select(ScheduledEvent).where(
            ScheduledEvent.status == PENDING, ScheduledEvent.due_at <= now
        ).order_by(ScheduledEvent.due_at).limit(limit).with_for_update(skip_locked=True))).all())
        for row in rows:
            row.status = PROCESSING; row.lease_token = uuid.uuid4(); row.lease_expires_at = now + timedelta(minutes=2)
        await self._session.flush()
        return rows

    async def fire(self, event: ScheduledEvent) -> None:
        if event.status != PROCESSING:
            return
        queue = OutboundQueue(self._session)
        request = await self._session.get(ConsultationRequest, event.consultation_request_id) if event.consultation_request_id else None
        if event.event_type == "diagnostic_followup":
            diagnostic = await self._session.get(DiagnosticSession, event.diagnostic_session_id)
            user = await self._session.get(User, event.user_id)
            if diagnostic and user and diagnostic.status in {"prepared", "diagnostic_active"} and user.communication_status == "subscribed":
                await queue.enqueue(user_id=event.user_id, channel="telegram_lead", payload={"kind":"message", "text":"Диагностика остановилась. Продолжите, когда будет удобно.", "buttons":[{"text":"Продолжить диагностику", "callback_data":f"diagnostic:resume:{diagnostic.id}"}]}, dedupe_key=f"scheduled:{event.id}:followup")
        elif request and event.event_type in {"appointment_t24", "appointment_t1"} and request.status == "scheduled":
            buttons = [] if event.event_type == "appointment_t1" else _appointment_buttons(request.id)
            when = format_moscow(request.appointment_at) if request.appointment_at else "назначенное время"
            text = f"Напоминаем: консультация {when} — через час." if event.event_type == "appointment_t1" else f"Напоминаем о консультации {when} завтра. Подтвердите, перенесите или отмените встречу."
            await queue.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message", "text":text, "buttons":buttons}, dedupe_key=f"scheduled:{event.id}:reminder")
        elif request and event.event_type == "appointment_auto_cancel" and request.status == "scheduled" and request.confirmation_state == "pending":
            request.status = "cancelled"
            await self.cancel_for_consultation(request.id)
            when = format_moscow(request.appointment_at) if request.appointment_at else "назначенное время"
            await queue.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message", "text":f"Время консультации {when} освобождено, потому что подтверждение не было получено.", "buttons":[]}, dedupe_key=f"scheduled:{event.id}:cancelled")
        event.status = FIRED; event.fired_at = datetime.now(timezone.utc); event.lease_token = None; event.lease_expires_at = None


class ScheduledEventWorker:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None: self._factory = factory
    async def run_once(self, *, limit: int = 20) -> int:
        async with session_scope(self._factory) as session:
            service = ScheduledEventService(session); events = await service.claim_due(limit=limit)
            for event in events: await service.fire(event)
            return len(events)


def _appointment_buttons(request_id: uuid.UUID) -> list[dict[str, str]]:
    return [
        {"text":"Подтвердить", "callback_data":f"consult:confirm:{request_id}"},
        {"text":"Перенести", "callback_data":f"consult:reschedule:{request_id}"},
        {"text":"Отменить", "callback_data":f"consult:cancel:{request_id}"},
    ]
