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
    RadarProfileVersion,
    RadarSearchProfile,
    RadarSignal,
    RadarSource,
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
        payload = await self._alert_payload(signal=signal, receipt=receipt)
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

    async def _alert_payload(
        self, *, signal: RadarSignal, receipt: RadarObservationReceipt
    ) -> dict[str, object]:
        content = receipt.payload.get("content") if isinstance(receipt.payload, dict) else None
        text = content.get("text") if isinstance(content, dict) else None
        links = receipt.payload.get("links") if isinstance(receipt.payload, dict) else None
        message_url = links.get("message_url") if isinstance(links, dict) else None
        source = await self._session.get(RadarSource, receipt.source_id)
        profile_name = None
        if signal.profile_version_id is not None:
            profile_name = await self._session.scalar(
                select(RadarSearchProfile.name)
                .join(
                    RadarProfileVersion,
                    (RadarProfileVersion.tenant_id == RadarSearchProfile.tenant_id)
                    & (RadarProfileVersion.profile_id == RadarSearchProfile.id),
                )
                .where(
                    RadarProfileVersion.tenant_id == signal.tenant_id,
                    RadarProfileVersion.id == signal.profile_version_id,
                )
            )
        source_label = None
        if source is not None:
            source_label = source.title or source.username or str(source.peer_id)
        return {
            "kind": "radar_signal",
            "signal_id": str(signal.id),
            "observation_id": str(receipt.observation_id),
            "source_id": str(receipt.source_id),
            "source_label": source_label or str(receipt.source_id),
            "message_id": receipt.message_id,
            "message_url": message_url if isinstance(message_url, str) else None,
            "text": text if isinstance(text, str) else "",
            "published_at": receipt.published_at.isoformat() if receipt.published_at else None,
            "detected_at": receipt.detected_at.isoformat(),
            "freshness_expires_at": (
                signal.freshness_expires_at.isoformat() if signal.freshness_expires_at else None
            ),
            "profile_name": profile_name,
            "matched_rule_keys": signal.matched_rule_keys,
            "reason": (
                f"совпали правила: {', '.join(signal.matched_rule_keys)}"
                if signal.matched_rule_keys
                else "совпадение профиля"
            ),
        }


# Kept for unit tests that project without a live DB session.
def _alert_payload(*, signal: RadarSignal, receipt: RadarObservationReceipt) -> dict[str, object]:
    content = receipt.payload.get("content") if isinstance(receipt.payload, dict) else None
    text = content.get("text") if isinstance(content, dict) else None
    links = receipt.payload.get("links") if isinstance(receipt.payload, dict) else None
    message_url = links.get("message_url") if isinstance(links, dict) else None
    return {
        "kind": "radar_signal",
        "signal_id": str(signal.id),
        "observation_id": str(receipt.observation_id),
        "source_id": str(receipt.source_id),
        "source_label": str(receipt.source_id),
        "message_id": receipt.message_id,
        "message_url": message_url if isinstance(message_url, str) else None,
        "text": text if isinstance(text, str) else "",
        "published_at": receipt.published_at.isoformat() if receipt.published_at else None,
        "detected_at": receipt.detected_at.isoformat(),
        "freshness_expires_at": (
            signal.freshness_expires_at.isoformat() if signal.freshness_expires_at else None
        ),
        "profile_name": None,
        "matched_rule_keys": signal.matched_rule_keys,
        "reason": (
            f"совпали правила: {', '.join(signal.matched_rule_keys)}"
            if signal.matched_rule_keys
            else "совпадение профиля"
        ),
    }
