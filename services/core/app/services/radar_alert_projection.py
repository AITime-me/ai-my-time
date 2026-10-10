"""Project matched Radar signals into the isolated Radar Bot outbox."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    RadarAlertOutbox,
    RadarDestination,
    RadarObservationReceipt,
    RadarProfileDestination,
    RadarSignal,
)


class RadarAlertProjectionService:
    """Create one delivery intent per verified bound destination.

    The unique database key is the dedupe boundary: repeating ingress or a
    future replay never creates another owner-visible alert intent.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def project(self, *, signal: RadarSignal, receipt: RadarObservationReceipt) -> int:
        if signal.status != "matched" or signal.profile_version_id is None:
            return 0
        destinations = (
            await self._session.scalars(
                select(RadarDestination)
                .join(
                    RadarProfileDestination,
                    (RadarProfileDestination.tenant_id == RadarDestination.tenant_id)
                    & (RadarProfileDestination.destination_id == RadarDestination.id),
                )
                .where(
                    RadarDestination.tenant_id == signal.tenant_id,
                    RadarProfileDestination.profile_version_id == signal.profile_version_id,
                    RadarDestination.enabled.is_(True),
                    RadarDestination.verification_state == "verified",
                )
                .order_by(RadarDestination.id)
            )
        ).all()
        payload = _alert_payload(signal=signal, receipt=receipt)
        created = 0
        for destination in destinations:
            statement = (
                insert(RadarAlertOutbox)
                .values(
                    tenant_id=signal.tenant_id,
                    signal_id=signal.id,
                    destination_id=destination.id,
                    payload=payload,
                    status="pending",
                )
                .on_conflict_do_nothing(
                    constraint="uq_radar_alert_outbox_signal_destination"
                )
                .returning(RadarAlertOutbox.id)
            )
            if await self._session.scalar(statement) is not None:
                created += 1
        return created


def _alert_payload(*, signal: RadarSignal, receipt: RadarObservationReceipt) -> dict[str, object]:
    """Keep projection deterministic and provider-neutral; rendering comes later."""

    content = receipt.payload.get("content") if isinstance(receipt.payload, dict) else None
    text = content.get("text") if isinstance(content, dict) else None
    return {
        "kind": "radar_signal",
        "signal_id": str(signal.id),
        "observation_id": str(receipt.observation_id),
        "source_id": str(receipt.source_id),
        "message_id": receipt.message_id,
        "text": text if isinstance(text, str) else "",
        "published_at": receipt.published_at.isoformat() if receipt.published_at else None,
        "detected_at": receipt.detected_at.isoformat(),
        "freshness_expires_at": (
            signal.freshness_expires_at.isoformat() if signal.freshness_expires_at else None
        ),
        "matched_rule_keys": signal.matched_rule_keys,
    }
