"""Safe end-to-end operational trace projections without raw webhook payloads."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, OperationalLogEvent, OutboundMessage
from app.schemas.admin import AdminOperationalTrace, AdminOperationalTraceEvent


class AdminTraceReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_person(self, user_id: uuid.UUID, *, limit: int = 100) -> AdminOperationalTrace:
        events = (await self._session.scalars(select(Event).where(Event.user_id == user_id))).all()
        outbox = (await self._session.scalars(select(OutboundMessage).where(OutboundMessage.user_id == user_id))).all()
        logs = (await self._session.scalars(select(OperationalLogEvent).where(OperationalLogEvent.user_id == user_id))).all()
        trace = [AdminOperationalTraceEvent(occurred_at=row.occurred_at, component="domain", event_type=row.kind, status="recorded", diagnostic_session_id=_session_id(row.payload_json)) for row in events]
        trace += [AdminOperationalTraceEvent(occurred_at=row.sent_at or row.created_at, component="outbox", event_type="telegram_delivery", status=row.status, outbox_message_id=row.id) for row in outbox]
        trace += [AdminOperationalTraceEvent(occurred_at=row.created_at, component=row.component, event_type=row.event_type, status=row.status, diagnostic_session_id=row.diagnostic_session_id, outbox_message_id=row.outbox_message_id) for row in logs]
        trace.sort(key=lambda item: item.occurred_at, reverse=True)
        return AdminOperationalTrace(user_id=user_id, items=trace[:limit])


def _session_id(payload: dict[str, object]) -> uuid.UUID | None:
    value = payload.get("diagnostic_session_id")
    try:
        return uuid.UUID(str(value)) if value else None
    except (ValueError, TypeError):
        return None
