"""Durable internal ingress for Reader observations."""

from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RadarObservationReceipt, RadarSource
from app.schemas.radar_v1 import RadarAckStatus, RadarObservationAckV1, RadarObservationV1
from app.services.radar_config import RadarConfigService
from app.services.radar_reader_auth import RadarReaderPrincipal


class RadarIngressError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _payload_hash(observation: RadarObservationV1) -> tuple[dict, str]:
    payload = observation.model_dump(mode="json")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return payload, hashlib.sha256(encoded).hexdigest()


class RadarIngressService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def accept(
        self, *, principal: RadarReaderPrincipal, observation: RadarObservationV1
    ) -> RadarObservationAckV1:
        source_id = self._parse_source_id(observation.source_id)
        source = await self._session.scalar(
            select(RadarSource).where(
                RadarSource.tenant_id == principal.tenant_id,
                RadarSource.reader_id == principal.reader_id,
                RadarSource.id == source_id,
                RadarSource.enabled.is_(True),
                RadarSource.is_approved.is_(True),
            )
        )
        if source is None:
            raise RadarIngressError("source_forbidden", "source is not authorized for this reader")
        if (
            source.connector != observation.connector
            or source.peer_type != observation.peer_type.value
            or str(source.peer_id) != observation.peer_id
        ):
            raise RadarIngressError("source_forbidden", "source identity does not match observation")

        current_manifest = await RadarConfigService(self._session).build_reader_manifest(principal)
        if observation.manifest_version != current_manifest.manifest_version:
            raise RadarIngressError("source_forbidden", "reader manifest is stale")

        payload, payload_sha256 = _payload_hash(observation)
        existing = await self._session.scalar(
            select(RadarObservationReceipt).where(
                RadarObservationReceipt.tenant_id == principal.tenant_id,
                RadarObservationReceipt.observation_id == observation.observation_id,
            )
        )
        if existing is not None:
            if existing.payload_sha256 != payload_sha256:
                raise RadarIngressError(
                    "idempotency_conflict", "observation_id was already used with another payload"
                )
            return RadarObservationAckV1(
                observation_id=observation.observation_id,
                receipt_id=existing.id,
                status=RadarAckStatus.DUPLICATE,
            )

        receipt = RadarObservationReceipt(
            tenant_id=principal.tenant_id,
            reader_id=principal.reader_id,
            source_id=source.id,
            observation_id=observation.observation_id,
            manifest_version=observation.manifest_version,
            message_id=observation.message_id,
            revision_fingerprint=observation.revision_fingerprint,
            payload_sha256=payload_sha256,
            event_kind=observation.event_kind.value,
            origin=observation.origin.value,
            published_at=observation.published_at,
            detected_at=observation.detected_at,
            edited_at=observation.edited_at,
            payload=payload,
        )
        self._session.add(receipt)
        await self._session.flush()
        return RadarObservationAckV1(
            observation_id=observation.observation_id,
            receipt_id=receipt.id,
            status=RadarAckStatus.ACCEPTED,
        )

    @staticmethod
    def _parse_source_id(raw: str) -> uuid.UUID:
        try:
            return uuid.UUID(raw)
        except ValueError as error:
            raise RadarIngressError("source_forbidden", "source is not authorized for this reader") from error
