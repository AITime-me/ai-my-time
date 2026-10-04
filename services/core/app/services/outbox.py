"""Provider-neutral durable outbound queue. No Telegram I/O belongs here."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboundMessage


class OutboundQueue:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        user_id: uuid.UUID,
        channel: str,
        payload: dict[str, object],
        dedupe_key: str,
    ) -> OutboundMessage:
        statement = (
            insert(OutboundMessage)
            .values(
                user_id=user_id,
                channel=channel,
                payload_json=payload,
                dedupe_key=dedupe_key,
                status="pending",
            )
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
            .returning(OutboundMessage.id)
        )
        created_id = await self._session.scalar(statement)
        if created_id is not None:
            row = await self._session.get(OutboundMessage, created_id)
            assert row is not None
            return row
        row = await self._session.scalar(
            select(OutboundMessage).where(OutboundMessage.dedupe_key == dedupe_key)
        )
        if row is None:
            raise RuntimeError("outbox conflict row missing")
        # Stable semantic keys must not permanently silence a message after
        # terminal delivery failure. Reclaim only failed rows; pending/sent stay
        # idempotent so retries cannot create a second logical copy.
        if row.status == "failed":
            row.status = "pending"
            row.payload_json = payload
            row.attempt_count = 0
            row.lease_token = None
            row.lease_expires_at = None
            row.last_error_code = None
            row.sent_at = None
        return row
