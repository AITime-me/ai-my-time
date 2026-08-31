"""Safe end-to-end operational trace projections without raw webhook payloads."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event
from app.schemas.admin import AdminOperationalTrace, AdminOperationalTraceEvent

_BUSINESS_EVENT_KINDS = {
    "channel_clicked",
    "consultation_requested",
    "repeat_consultation_requested",
    "profile_answered",
    "diagnostic_started",
    "diagnostic_completed",
    "content_subscribed",
    "content_unsubscribed",
}


class AdminTraceReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_person(self, user_id: uuid.UUID, *, limit: int = 100) -> AdminOperationalTrace:
        events = (await self._session.scalars(select(Event).where(Event.user_id == user_id))).all()
        # The person card is a business history, not an operational console.
        # Delivery/retry telemetry remains durable for incident diagnosis but is
        # intentionally excluded here, as are raw transport logs.
        trace = [
            AdminOperationalTraceEvent(
                occurred_at=row.occurred_at,
                component="domain",
                event_type=row.kind,
                status="recorded",
                diagnostic_session_id=_session_id(row.payload_json),
            )
            for row in events
            if row.kind in _BUSINESS_EVENT_KINDS
        ]
        trace.sort(key=lambda item: item.occurred_at, reverse=True)
        return AdminOperationalTrace(user_id=user_id, items=trace[:limit])


def _session_id(payload: dict[str, object]) -> uuid.UUID | None:
    value = payload.get("diagnostic_session_id")
    try:
        return uuid.UUID(str(value)) if value else None
    except (ValueError, TypeError):
        return None
