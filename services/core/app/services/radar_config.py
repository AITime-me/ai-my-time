"""Tenant-scoped Demand Radar configuration services (Admin + Reader manifest)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditEvent,
    RadarDestination,
    RadarProfileDestination,
    RadarProfileSource,
    RadarProfileVersion,
    RadarReader,
    RadarSearchProfile,
    RadarSearchRule,
    RadarSource,
    RadarTenant,
    RadarTenantAdmin,
)
from app.schemas.radar_admin import (
    RadarDestinationCreate,
    RadarDestinationView,
    RadarProfileActivate,
    RadarProfileCreate,
    RadarProfileVersionCreate,
    RadarProfileVersionView,
    RadarProfileView,
    RadarReaderView,
    RadarRuleView,
    RadarSourceCreate,
    RadarSourcePatch,
    RadarSourceView,
)
from app.schemas.radar_v1 import (
    RadarMonitoringCapability,
    RadarPeerType,
    RadarReaderManifestV1,
    RadarSourceManifestItemV1,
    RadarSourceType,
)
from app.services.radar_reader_auth import RadarReaderPrincipal

_MANIFEST_TTL = timedelta(minutes=15)


class RadarConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class RadarConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_tenant_membership(
        self, *, actor_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> RadarTenant:
        membership = await self._session.get(RadarTenantAdmin, (tenant_id, actor_id))
        if membership is None:
            raise RadarConfigError("tenant_forbidden", "radar tenant not found")
        tenant = await self._session.get(RadarTenant, tenant_id)
        if tenant is None or not tenant.enabled:
            raise RadarConfigError("tenant_forbidden", "radar tenant not found")
        return tenant

    def _audit(
        self,
        *,
        actor_id: uuid.UUID,
        action: str,
        object_type: str,
        object_id: uuid.UUID | None,
        tenant_id: uuid.UUID,
        delta: dict[str, object],
    ) -> None:
        payload = {"tenant_id": str(tenant_id), **delta}
        self._session.add(
            AdminAuditEvent(
                actor_id=actor_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                delta_json=payload,
            )
        )

    @staticmethod
    def _source_view(row: RadarSource) -> RadarSourceView:
        return RadarSourceView(
            id=row.id,
            tenant_id=row.tenant_id,
            reader_id=row.reader_id,
            connector="telegram",
            peer_type=row.peer_type,
            peer_id=row.peer_id,
            source_type=row.source_type,
            username=row.username,
            title=row.title,
            is_public=row.is_public,
            is_approved=row.is_approved,
            enabled=row.enabled,
            monitoring_capability=row.monitoring_capability,
            config_version=row.config_version,
            activated_at=row.activated_at,
            last_read_at=row.last_read_at,
            last_message_at=row.last_message_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_sources(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> list[RadarSourceView]:
        rows = (
            await self._session.scalars(
                select(RadarSource)
                .where(RadarSource.tenant_id == tenant_id)
                .order_by(RadarSource.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [self._source_view(row) for row in rows]

    async def create_source(
        self, *, actor_id: uuid.UUID, tenant_id: uuid.UUID, payload: RadarSourceCreate
    ) -> RadarSourceView:
        reader = await self._session.scalar(
            select(RadarReader).where(
                RadarReader.tenant_id == tenant_id, RadarReader.id == payload.reader_id
            )
        )
        if reader is None:
            raise RadarConfigError("reader_not_found", "reader not found")
        row = RadarSource(
            tenant_id=tenant_id,
            reader_id=payload.reader_id,
            peer_type=payload.peer_type,
            peer_id=payload.peer_id,
            source_type=payload.source_type,
            username=payload.username,
            title=payload.title,
            is_public=payload.is_public,
            is_approved=payload.is_approved,
            enabled=payload.enabled,
            monitoring_capability=payload.monitoring_capability,
            activated_at=payload.activated_at,
            config_version=1,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise RadarConfigError("source_conflict", "source already exists") from error
        self._audit(
            actor_id=actor_id,
            action="radar.source.created",
            object_type="radar_source",
            object_id=row.id,
            tenant_id=tenant_id,
            delta={"peer_type": row.peer_type, "peer_id": row.peer_id},
        )
        return self._source_view(row)

    async def patch_source(
        self,
        *,
        actor_id: uuid.UUID,
        tenant_id: uuid.UUID,
        source_id: uuid.UUID,
        payload: RadarSourcePatch,
    ) -> RadarSourceView:
        values: dict[str, object] = {"config_version": RadarSource.config_version + 1}
        if payload.reader_id is not None:
            reader = await self._session.scalar(
                select(RadarReader).where(
                    RadarReader.tenant_id == tenant_id, RadarReader.id == payload.reader_id
                )
            )
            if reader is None:
                raise RadarConfigError("reader_not_found", "reader not found")
            values["reader_id"] = payload.reader_id
        if payload.username is not None:
            values["username"] = payload.username
        if payload.title is not None:
            values["title"] = payload.title
        if payload.is_public is not None:
            values["is_public"] = payload.is_public
        if payload.is_approved is not None:
            values["is_approved"] = payload.is_approved
        if payload.enabled is not None:
            values["enabled"] = payload.enabled
        if payload.monitoring_capability is not None:
            values["monitoring_capability"] = payload.monitoring_capability
        if payload.activated_at is not None:
            values["activated_at"] = payload.activated_at

        result = await self._session.execute(
            update(RadarSource)
            .where(
                RadarSource.tenant_id == tenant_id,
                RadarSource.id == source_id,
                RadarSource.config_version == payload.expected_config_version,
            )
            .values(**values)
            .returning(RadarSource)
        )
        row = result.scalar_one_or_none()
        if row is None:
            exists = await self._session.scalar(
                select(RadarSource.id).where(
                    RadarSource.tenant_id == tenant_id, RadarSource.id == source_id
                )
            )
            if exists is None:
                raise RadarConfigError("source_not_found", "source not found")
            raise RadarConfigError("source_version_conflict", "source_version_conflict")
        self._audit(
            actor_id=actor_id,
            action="radar.source.updated",
            object_type="radar_source",
            object_id=row.id,
            tenant_id=tenant_id,
            delta={
                "config_version": row.config_version,
                "enabled": row.enabled,
                "is_approved": row.is_approved,
            },
        )
        return self._source_view(row)

    async def list_readers(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> list[RadarReaderView]:
        rows = (
            await self._session.scalars(
                select(RadarReader)
                .where(RadarReader.tenant_id == tenant_id)
                .order_by(RadarReader.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [
            RadarReaderView(
                id=row.id,
                tenant_id=row.tenant_id,
                reader_key=row.reader_key,
                enabled=row.enabled,
                credential_key_id=row.credential_key_id,
                last_heartbeat_at=row.last_heartbeat_at,
                connection_status=row.connection_status,
                telegram_authorization_status=row.telegram_authorization_status,
                applied_manifest_version=row.applied_manifest_version,
                journal_backlog=row.journal_backlog,
                safe_error=row.safe_error,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def list_destinations(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> list[RadarDestinationView]:
        rows = (
            await self._session.scalars(
                select(RadarDestination)
                .where(RadarDestination.tenant_id == tenant_id)
                .order_by(RadarDestination.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [self._destination_view(row) for row in rows]

    @staticmethod
    def _destination_view(row: RadarDestination) -> RadarDestinationView:
        return RadarDestinationView(
            id=row.id,
            tenant_id=row.tenant_id,
            bot_binding_key=row.bot_binding_key,
            chat_id=row.chat_id,
            enabled=row.enabled,
            verification_state=row.verification_state,
            verified_at=row.verified_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_destination(
        self, *, actor_id: uuid.UUID, tenant_id: uuid.UUID, payload: RadarDestinationCreate
    ) -> RadarDestinationView:
        row = RadarDestination(
            tenant_id=tenant_id,
            bot_binding_key=payload.bot_binding_key,
            chat_id=payload.chat_id,
            enabled=payload.enabled,
            verification_state="unverified",
            verified_at=None,
        )
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise RadarConfigError("destination_conflict", "destination already exists") from error
        self._audit(
            actor_id=actor_id,
            action="radar.destination.created",
            object_type="radar_destination",
            object_id=row.id,
            tenant_id=tenant_id,
            delta={"bot_binding_key": row.bot_binding_key, "chat_id": row.chat_id},
        )
        return self._destination_view(row)

    async def list_profiles(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> list[RadarProfileView]:
        rows = (
            await self._session.scalars(
                select(RadarSearchProfile)
                .where(RadarSearchProfile.tenant_id == tenant_id)
                .order_by(RadarSearchProfile.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [self._profile_view(row) for row in rows]

    @staticmethod
    def _profile_view(row: RadarSearchProfile) -> RadarProfileView:
        """Project already-loaded scalar columns only (no lazy/async IO)."""

        return RadarProfileView(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            enabled=row.enabled,
            active_version_id=row.active_version_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _refreshed_profile_view(self, row: RadarSearchProfile) -> RadarProfileView:
        # After INSERT/UPDATE, server defaults / onupdate may expire columns;
        # refresh explicitly so _profile_view never triggers async lazy IO.
        await self._session.refresh(row)
        return self._profile_view(row)

    async def create_profile(
        self, *, actor_id: uuid.UUID, tenant_id: uuid.UUID, payload: RadarProfileCreate
    ) -> RadarProfileView:
        row = RadarSearchProfile(
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            enabled=payload.enabled,
        )
        self._session.add(row)
        await self._session.flush()
        self._audit(
            actor_id=actor_id,
            action="radar.profile.created",
            object_type="radar_search_profile",
            object_id=row.id,
            tenant_id=tenant_id,
            delta={"name": row.name},
        )
        return await self._refreshed_profile_view(row)

    async def create_profile_version(
        self,
        *,
        actor_id: uuid.UUID,
        tenant_id: uuid.UUID,
        profile_id: uuid.UUID,
        payload: RadarProfileVersionCreate,
    ) -> RadarProfileVersionView:
        profile = await self._session.scalar(
            select(RadarSearchProfile)
            .where(
                RadarSearchProfile.tenant_id == tenant_id,
                RadarSearchProfile.id == profile_id,
            )
            .with_for_update()
        )
        if profile is None:
            raise RadarConfigError("profile_not_found", "profile not found")

        rule_keys = [rule.rule_key for rule in payload.rules]
        if len(rule_keys) != len(set(rule_keys)):
            raise RadarConfigError("rule_conflict", "duplicate rule_key")
        if len(payload.source_ids) != len(set(payload.source_ids)):
            raise RadarConfigError("binding_conflict", "duplicate source binding")
        if len(payload.destination_ids) != len(set(payload.destination_ids)):
            raise RadarConfigError("binding_conflict", "duplicate destination binding")

        for source_id in payload.source_ids:
            exists = await self._session.scalar(
                select(RadarSource.id).where(
                    RadarSource.tenant_id == tenant_id, RadarSource.id == source_id
                )
            )
            if exists is None:
                raise RadarConfigError("source_not_found", "source not found")
        for destination_id in payload.destination_ids:
            exists = await self._session.scalar(
                select(RadarDestination.id).where(
                    RadarDestination.tenant_id == tenant_id,
                    RadarDestination.id == destination_id,
                )
            )
            if exists is None:
                raise RadarConfigError("destination_not_found", "destination not found")

        next_version = (
            await self._session.scalar(
                select(func.coalesce(func.max(RadarProfileVersion.version), 0)).where(
                    RadarProfileVersion.tenant_id == tenant_id,
                    RadarProfileVersion.profile_id == profile_id,
                )
            )
            or 0
        ) + 1

        version = RadarProfileVersion(
            tenant_id=tenant_id,
            profile_id=profile_id,
            version=next_version,
            rule_schema_version=payload.rule_schema_version,
            category=payload.category,
            freshness_seconds=payload.freshness_seconds,
            normalizer_version=payload.normalizer_version,
        )
        self._session.add(version)
        await self._session.flush()

        for rule in payload.rules:
            self._session.add(
                RadarSearchRule(
                    tenant_id=tenant_id,
                    profile_version_id=version.id,
                    rule_key=rule.rule_key,
                    kind=rule.kind,
                    enabled=rule.enabled,
                    expression=rule.expression,
                    weight=rule.weight,
                )
            )
        for source_id in payload.source_ids:
            self._session.add(
                RadarProfileSource(
                    tenant_id=tenant_id,
                    profile_version_id=version.id,
                    source_id=source_id,
                )
            )
        for destination_id in payload.destination_ids:
            self._session.add(
                RadarProfileDestination(
                    tenant_id=tenant_id,
                    profile_version_id=version.id,
                    destination_id=destination_id,
                )
            )
        await self._session.flush()
        self._audit(
            actor_id=actor_id,
            action="radar.profile_version.created",
            object_type="radar_profile_version",
            object_id=version.id,
            tenant_id=tenant_id,
            delta={"profile_id": str(profile_id), "version": version.version},
        )
        return await self._version_view(version)

    async def _version_view(self, version: RadarProfileVersion) -> RadarProfileVersionView:
        rules = (
            await self._session.scalars(
                select(RadarSearchRule)
                .where(
                    RadarSearchRule.tenant_id == version.tenant_id,
                    RadarSearchRule.profile_version_id == version.id,
                )
                .order_by(RadarSearchRule.rule_key)
            )
        ).all()
        source_ids = list(
            await self._session.scalars(
                select(RadarProfileSource.source_id).where(
                    RadarProfileSource.tenant_id == version.tenant_id,
                    RadarProfileSource.profile_version_id == version.id,
                )
            )
        )
        destination_ids = list(
            await self._session.scalars(
                select(RadarProfileDestination.destination_id).where(
                    RadarProfileDestination.tenant_id == version.tenant_id,
                    RadarProfileDestination.profile_version_id == version.id,
                )
            )
        )
        return RadarProfileVersionView(
            id=version.id,
            tenant_id=version.tenant_id,
            profile_id=version.profile_id,
            version=version.version,
            rule_schema_version=version.rule_schema_version,
            category=version.category,
            freshness_seconds=version.freshness_seconds,
            normalizer_version=version.normalizer_version,
            activated_at=version.activated_at,
            created_at=version.created_at,
            rules=[
                RadarRuleView(
                    id=rule.id,
                    rule_key=rule.rule_key,
                    kind=rule.kind,
                    enabled=rule.enabled,
                    expression=rule.expression,
                    weight=rule.weight,
                )
                for rule in rules
            ],
            source_ids=source_ids,
            destination_ids=destination_ids,
        )

    async def activate_profile_version(
        self,
        *,
        actor_id: uuid.UUID,
        tenant_id: uuid.UUID,
        profile_id: uuid.UUID,
        payload: RadarProfileActivate,
    ) -> RadarProfileView:
        profile = await self._session.scalar(
            select(RadarSearchProfile)
            .where(
                RadarSearchProfile.tenant_id == tenant_id,
                RadarSearchProfile.id == profile_id,
            )
            .with_for_update()
        )
        if profile is None:
            raise RadarConfigError("profile_not_found", "profile not found")

        version = await self._session.scalar(
            select(RadarProfileVersion).where(
                RadarProfileVersion.tenant_id == tenant_id,
                RadarProfileVersion.profile_id == profile_id,
                RadarProfileVersion.id == payload.version_id,
            )
        )
        if version is None:
            raise RadarConfigError("version_not_found", "profile version not found")

        if profile.active_version_id == version.id:
            return await self._refreshed_profile_view(profile)

        now = datetime.now(timezone.utc)
        profile.active_version_id = version.id
        version.activated_at = now
        await self._session.flush()
        self._audit(
            actor_id=actor_id,
            action="radar.profile.activated",
            object_type="radar_search_profile",
            object_id=profile.id,
            tenant_id=tenant_id,
            delta={"active_version_id": str(version.id), "version": version.version},
        )
        return await self._refreshed_profile_view(profile)

    @staticmethod
    def compute_manifest_version(
        *, reader_id: uuid.UUID, sources: list[RadarSource]
    ) -> str:
        payload = {
            "reader_id": str(reader_id),
            "sources": [
                {
                    "source_id": str(source.id),
                    "config_version": source.config_version,
                    "connector": source.connector,
                    "peer_type": source.peer_type,
                    "peer_id": str(source.peer_id),
                    "source_type": source.source_type,
                    "enabled": source.enabled,
                    "approved": source.is_approved,
                    "monitoring_capability": source.monitoring_capability,
                    "activated_at": (
                        (source.activated_at or source.created_at)
                        .astimezone(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z")
                    ),
                }
                for source in sorted(sources, key=lambda item: str(item.id))
            ],
        }
        digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        return digest[:64]

    async def build_reader_manifest(
        self, principal: RadarReaderPrincipal
    ) -> RadarReaderManifestV1:
        sources = list(
            await self._session.scalars(
                select(RadarSource)
                .where(
                    RadarSource.tenant_id == principal.tenant_id,
                    RadarSource.reader_id == principal.reader_id,
                    RadarSource.enabled.is_(True),
                    RadarSource.is_approved.is_(True),
                )
                .order_by(RadarSource.id)
            )
        )
        if not sources:
            raise RadarConfigError("manifest_unavailable", "manifest unavailable")

        issued_at = datetime.now(timezone.utc)
        items = [
            RadarSourceManifestItemV1(
                source_id=str(source.id),
                connector="telegram",
                peer_type=RadarPeerType(source.peer_type),
                peer_id=str(source.peer_id),
                source_type=RadarSourceType(source.source_type),
                activated_at=source.activated_at or source.created_at,
                enabled=source.enabled,
                approved=source.is_approved,
                monitoring_capability=RadarMonitoringCapability(source.monitoring_capability),
            )
            for source in sources
        ]
        return RadarReaderManifestV1(
            schema_version=1,
            reader_id=str(principal.reader_id),
            manifest_version=self.compute_manifest_version(
                reader_id=principal.reader_id, sources=sources
            ),
            issued_at=issued_at,
            expires_at=issued_at + _MANIFEST_TTL,
            sources=items,
        )
