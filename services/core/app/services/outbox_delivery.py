"""A provider-free worker contract for durable outbound messages.

It deliberately contains no bot token, HTTP call or Telegram URL. A real
provider adapter will be injected later, after infrastructure approval.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import OutboundMessage, User, UserIdentity
from app.db.session import session_scope

MAX_DELIVERY_ATTEMPTS = 5
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 300


@dataclass(frozen=True)
class OutboundDelivery:
    message_id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    payload: dict[str, object]
    lease_token: uuid.UUID
    recipient_id: str | None = None


class OutboundTransport(Protocol):
    async def deliver(self, message: OutboundDelivery) -> None: ...


class OutboundDeliveryService:
    """Claims work once, then marks that exact lease sent or retryable."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, limit: int, lease_seconds: int = 60) -> list[OutboundDelivery]:
        if not 1 <= limit <= 100:
            raise ValueError("outbound claim limit must be between 1 and 100")
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(OutboundMessage)
            .where(
                OutboundMessage.status == "processing",
                OutboundMessage.lease_expires_at < now,
            )
            .values(status="pending", lease_token=None, lease_expires_at=None)
        )
        rows = list(
            (
                await self._session.scalars(
                    select(OutboundMessage)
                    .where(OutboundMessage.status == "pending")
                    .order_by(OutboundMessage.created_at, OutboundMessage.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        deliveries: list[OutboundDelivery] = []
        for row in rows:
            lease_token = uuid.uuid4()
            row.status = "processing"
            row.lease_token = lease_token
            row.lease_expires_at = now + timedelta(seconds=lease_seconds)
            row.attempt_count += 1
            row.last_error_code = None
            recipient_id = await self._session.scalar(
                select(UserIdentity.external_id).where(
                    UserIdentity.user_id == row.user_id,
                    UserIdentity.provider == "telegram",
                )
            )
            deliveries.append(
                OutboundDelivery(
                    message_id=row.id,
                    user_id=row.user_id,
                    channel=row.channel,
                    payload=row.payload_json,
                    lease_token=lease_token,
                    recipient_id=recipient_id,
                )
            )
        await self._session.flush()
        return deliveries

    async def mark_sent(self, delivery: OutboundDelivery) -> None:
        result = await self._session.execute(
            update(OutboundMessage)
            .where(
                OutboundMessage.id == delivery.message_id,
                OutboundMessage.status == "processing",
                OutboundMessage.lease_token == delivery.lease_token,
            )
            .values(
                status="sent",
                sent_at=datetime.now(timezone.utc),
                lease_token=None,
                lease_expires_at=None,
                last_error_code=None,
            )
        )
        if result.rowcount != 1:
            raise ValueError("outbound delivery lease is no longer active")
        if delivery.channel == "telegram_lead":
            await self._session.execute(
                update(User).where(User.id == delivery.user_id).values(telegram_reachability="allowed")
            )

    async def mark_retry(self, delivery: OutboundDelivery, *, error_code: str) -> None:
        attempt_count = await self._session.scalar(
            select(OutboundMessage.attempt_count).where(
                OutboundMessage.id == delivery.message_id,
                OutboundMessage.status == "processing",
                OutboundMessage.lease_token == delivery.lease_token,
            )
        )
        if attempt_count is None:
            raise ValueError("outbound delivery lease is no longer active")
        if attempt_count >= MAX_DELIVERY_ATTEMPTS:
            values = {
                "status": "failed",
                "lease_token": None,
                "lease_expires_at": None,
                "last_error_code": error_code[:120],
            }
        else:
            delay_seconds = min(RETRY_BASE_SECONDS * 2 ** (attempt_count - 1), RETRY_MAX_SECONDS)
            values = {
                "status": "processing",
                "lease_token": None,
                "lease_expires_at": datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
                "last_error_code": error_code[:120],
            }
        result = await self._session.execute(
            update(OutboundMessage)
            .where(
                OutboundMessage.id == delivery.message_id,
                OutboundMessage.status == "processing",
                OutboundMessage.lease_token == delivery.lease_token,
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise ValueError("outbound delivery lease is no longer active")
        if attempt_count >= MAX_DELIVERY_ATTEMPTS and delivery.channel == "telegram_lead":
            await self._session.execute(
                update(User).where(User.id == delivery.user_id).values(telegram_reachability="blocked")
            )


class OutboundWorker:
    """Runs a bounded batch through an injected transport; no network by default."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], transport: OutboundTransport) -> None:
        self._session_factory = session_factory
        self._transport = transport

    async def run_once(self, *, limit: int = 20) -> int:
        async with session_scope(self._session_factory) as session:
            deliveries = await OutboundDeliveryService(session).claim(limit=limit)
        sent_count = 0
        for delivery in deliveries:
            try:
                await self._transport.deliver(delivery)
            except Exception as error:
                async with session_scope(self._session_factory) as session:
                    await OutboundDeliveryService(session).mark_retry(
                        delivery, error_code=type(error).__name__
                    )
            else:
                async with session_scope(self._session_factory) as session:
                    await OutboundDeliveryService(session).mark_sent(delivery)
                sent_count += 1
        return sent_count
