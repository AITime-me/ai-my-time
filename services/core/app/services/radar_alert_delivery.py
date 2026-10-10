"""Lease, retry and freshness handling for the isolated Radar Bot outbox."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import session_scope
from app.models import RadarAlertOutbox, RadarDestination

MAX_RADAR_ALERT_ATTEMPTS = 5
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 300


@dataclass(frozen=True)
class RadarAlertDelivery:
    alert_id: uuid.UUID
    bot_binding_key: str
    chat_id: int
    payload: dict[str, object]
    lease_token: uuid.UUID


class RadarAlertDeliveryService:
    """Claims only fresh verified-destination alerts and finalizes one lease."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, limit: int, lease_seconds: int = 60) -> list[RadarAlertDelivery]:
        if not 1 <= limit <= 100:
            raise ValueError("radar alert claim limit must be between 1 and 100")
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(RadarAlertOutbox)
            .where(RadarAlertOutbox.status == "processing", RadarAlertOutbox.lease_expires_at < now)
            .values(status="pending", lease_token=None, lease_expires_at=None)
        )
        rows = (await self._session.execute(
            select(RadarAlertOutbox, RadarDestination)
            .join(RadarDestination, (RadarDestination.tenant_id == RadarAlertOutbox.tenant_id) & (RadarDestination.id == RadarAlertOutbox.destination_id))
            .where(RadarAlertOutbox.status == "pending")
            .order_by(RadarAlertOutbox.created_at, RadarAlertOutbox.id).limit(limit)
            .with_for_update(skip_locked=True)
        )).all()
        deliveries: list[RadarAlertDelivery] = []
        for alert, destination in rows:
            freshness, freshness_valid = _parse_freshness(alert.payload)
            if not freshness_valid:
                alert.status, alert.last_error_code = "skipped", "freshness_invalid"
                continue
            if freshness is not None and freshness <= now:
                alert.status, alert.last_error_code = "skipped", "freshness_expired"
                continue
            if (alert.payload.get("kind") != "radar_signal" or not destination.enabled
                    or destination.verification_state != "verified" or not destination.bot_binding_key.strip()
                    or destination.chat_id == 0):
                alert.status, alert.last_error_code = "skipped", "destination_or_payload_invalid"
                continue
            token = uuid.uuid4()
            alert.status, alert.lease_token = "processing", token
            alert.lease_expires_at = now + timedelta(seconds=lease_seconds)
            alert.attempt_count += 1
            alert.last_error_code = None
            deliveries.append(RadarAlertDelivery(alert.id, destination.bot_binding_key, destination.chat_id, alert.payload, token))
        await self._session.flush()
        return deliveries

    async def mark_sent(self, delivery: RadarAlertDelivery) -> None:
        result = await self._session.execute(update(RadarAlertOutbox).where(
            RadarAlertOutbox.id == delivery.alert_id, RadarAlertOutbox.status == "processing",
            RadarAlertOutbox.lease_token == delivery.lease_token,
        ).values(status="sent", sent_at=datetime.now(timezone.utc), lease_token=None, lease_expires_at=None, last_error_code=None))
        if result.rowcount != 1:
            raise ValueError("radar alert delivery lease is no longer active")

    async def mark_retry(self, delivery: RadarAlertDelivery, *, error_code: str) -> None:
        attempts = await self._session.scalar(select(RadarAlertOutbox.attempt_count).where(
            RadarAlertOutbox.id == delivery.alert_id, RadarAlertOutbox.status == "processing",
            RadarAlertOutbox.lease_token == delivery.lease_token,
        ))
        if attempts is None:
            raise ValueError("radar alert delivery lease is no longer active")
        values: dict[str, object] = {"lease_token": None, "last_error_code": error_code[:120]}
        if attempts >= MAX_RADAR_ALERT_ATTEMPTS:
            values.update(status="failed", lease_expires_at=None)
        else:
            delay = min(RETRY_BASE_SECONDS * 2 ** (attempts - 1), RETRY_MAX_SECONDS)
            values.update(status="processing", lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=delay))
        result = await self._session.execute(update(RadarAlertOutbox).where(
            RadarAlertOutbox.id == delivery.alert_id, RadarAlertOutbox.status == "processing",
            RadarAlertOutbox.lease_token == delivery.lease_token,
        ).values(**values))
        if result.rowcount != 1:
            raise ValueError("radar alert delivery lease is no longer active")


class RadarAlertWorker:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], transport) -> None:
        self._session_factory, self._transport = session_factory, transport

    async def run_once(self, *, limit: int = 20) -> int:
        async with session_scope(self._session_factory) as session:
            deliveries = await RadarAlertDeliveryService(session).claim(limit=limit)
        sent = 0
        for delivery in deliveries:
            try:
                await self._transport.deliver(delivery)
            except Exception as error:
                async with session_scope(self._session_factory) as session:
                    await RadarAlertDeliveryService(session).mark_retry(delivery, error_code=type(error).__name__)
            else:
                async with session_scope(self._session_factory) as session:
                    await RadarAlertDeliveryService(session).mark_sent(delivery)
                sent += 1
        return sent


def _parse_freshness(payload: dict) -> tuple[datetime | None, bool]:
    value = payload.get("freshness_expires_at")
    if value is None:
        return None, True
    if not isinstance(value, str) or not value:
        return None, False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None, False
    return (parsed, True) if parsed.tzinfo is not None else (None, False)
