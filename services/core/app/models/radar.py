"""Demand Radar configuration storage (tenant-scoped; no ingress/runtime)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import Timestamped


class RadarTenant(Timestamped, Base):
    __tablename__ = "radar_tenant"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_radar_tenant_slug"),
        CheckConstraint("raw_retention_days >= 1", name="ck_radar_tenant_raw_retention_days"),
        CheckConstraint("metadata_retention_days >= 0", name="ck_radar_tenant_metadata_retention_days"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    raw_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30")
    )
    metadata_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("90")
    )


class RadarTenantAdmin(Base):
    __tablename__ = "radar_tenant_admin"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_tenant_admin_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["admin_user_id"],
            ["admin_users.id"],
            name="fk_radar_tenant_admin_admin_user",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "role IN ('owner', 'operator')",
            name="ck_radar_tenant_admin_role",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    admin_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False, server_default="operator")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RadarReader(Timestamped, Base):
    __tablename__ = "radar_reader"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_reader_tenant_id"),
        UniqueConstraint("tenant_id", "reader_key", name="uq_radar_reader_tenant_reader_key"),
        UniqueConstraint("credential_key_id", name="uq_radar_reader_credential_key_id"),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_reader_tenant",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_radar_reader_last_heartbeat_enabled",
            "last_heartbeat_at",
            postgresql_where=text("enabled"),
        ),
        CheckConstraint("journal_backlog >= 0", name="ck_radar_reader_journal_backlog"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reader_key: Mapped[str] = mapped_column(String(128), nullable=False)
    credential_key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connection_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telegram_authorization_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    applied_manifest_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    journal_backlog: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    safe_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class RadarSource(Timestamped, Base):
    __tablename__ = "radar_source"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_source_tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "connector",
            "peer_type",
            "peer_id",
            name="uq_radar_source_tenant_connector_peer",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_source_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reader_id"],
            ["radar_reader.tenant_id", "radar_reader.id"],
            name="fk_radar_source_reader",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_radar_source_tenant_reader_enabled",
            "tenant_id",
            "reader_id",
            postgresql_where=text("enabled"),
        ),
        CheckConstraint("connector = 'telegram'", name="ck_radar_source_connector"),
        CheckConstraint("peer_id > 0", name="ck_radar_source_peer_id_positive"),
        CheckConstraint(
            "peer_type IN ('channel', 'supergroup', 'group', 'user')",
            name="ck_radar_source_peer_type",
        ),
        CheckConstraint(
            "source_type IN ('channel', 'supergroup', 'group', 'user')",
            name="ck_radar_source_source_type",
        ),
        CheckConstraint(
            "monitoring_capability IN ('realtime', 'history_only', 'unverified')",
            name="ck_radar_source_monitoring_capability",
        ),
        CheckConstraint("config_version >= 1", name="ck_radar_source_config_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    connector: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="telegram"
    )
    peer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    peer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    monitoring_capability: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unverified"
    )
    config_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RadarDestination(Timestamped, Base):
    __tablename__ = "radar_destination"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_destination_tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "bot_binding_key",
            "chat_id",
            name="uq_radar_destination_tenant_bot_chat",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_destination_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "verification_state IN ('unverified', 'pending', 'verified', 'rejected')",
            name="ck_radar_destination_verification_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bot_binding_key: Mapped[str] = mapped_column(String(128), nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    verification_state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unverified"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RadarObservationReceipt(Timestamped, Base):
    """Durable Reader receipt; matching and delivery are deliberately separate."""

    __tablename__ = "radar_observation_receipt"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "id", name="uq_radar_observation_receipt_tenant_id"
        ),
        UniqueConstraint(
            "tenant_id", "observation_id", name="uq_radar_observation_receipt_tenant_observation"
        ),
        ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_observation_receipt_tenant", ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reader_id"],
            ["radar_reader.tenant_id", "radar_reader.id"],
            name="fk_radar_observation_receipt_reader",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_id"],
            ["radar_source.tenant_id", "radar_source.id"],
            name="fk_radar_observation_receipt_source",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_radar_observation_receipt_tenant_source_message",
            "tenant_id",
            "source_id",
            "message_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    observation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    manifest_version: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RadarSignal(Timestamped, Base):
    """One durable matching outcome for a tenant and accepted observation.

    A signal is deliberately distinct from a delivery attempt: matching can be
    retried or reprojected without creating a second tenant-visible signal.
    """

    __tablename__ = "radar_signal"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_signal_tenant_id"),
        UniqueConstraint(
            "tenant_id", "observation_receipt_id", name="uq_radar_signal_tenant_receipt"
        ),
        ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_signal_tenant", ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "observation_receipt_id"],
            ["radar_observation_receipt.tenant_id", "radar_observation_receipt.id"],
            name="fk_radar_signal_receipt",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_signal_profile_version",
            ondelete="RESTRICT",
        ),
        Index("ix_radar_signal_tenant_status_created", "tenant_id", "status", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'matched', 'excluded', 'no_match', 'stale', 'deleted')",
            name="ck_radar_signal_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    observation_receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    matched_rule_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    excluded_rule_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    freshness_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RadarAlertOutbox(Timestamped, Base):
    """Tenant-local Radar Bot delivery intent, separate from Lead Bot outbox."""

    __tablename__ = "radar_alert_outbox"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "signal_id", "destination_id", name="uq_radar_alert_outbox_signal_destination"
        ),
        ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_alert_outbox_tenant", ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "signal_id"], ["radar_signal.tenant_id", "radar_signal.id"],
            name="fk_radar_alert_outbox_signal", ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "destination_id"], ["radar_destination.tenant_id", "radar_destination.id"],
            name="fk_radar_alert_outbox_destination", ondelete="RESTRICT",
        ),
        Index("ix_radar_alert_outbox_status_created", "status", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'skipped')",
            name="ck_radar_alert_outbox_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_radar_alert_outbox_attempt_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    signal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RadarSearchProfile(Timestamped, Base):
    __tablename__ = "radar_search_profile"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_search_profile_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_search_profile_tenant",
            ondelete="RESTRICT",
        ),
        # Active version FK is declared after RadarProfileVersion (deferred).
        ForeignKeyConstraint(
            ["tenant_id", "id", "active_version_id"],
            [
                "radar_profile_version.tenant_id",
                "radar_profile_version.profile_id",
                "radar_profile_version.id",
            ],
            name="fk_radar_search_profile_active_version",
            ondelete="RESTRICT",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class RadarProfileVersion(Base):
    """Immutable profile version row; activation is a pointer on the profile."""

    __tablename__ = "radar_profile_version"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_radar_profile_version_tenant_id"),
        UniqueConstraint(
            "tenant_id", "profile_id", "id", name="uq_radar_profile_version_tenant_profile_id"
        ),
        UniqueConstraint(
            "tenant_id",
            "profile_id",
            "version",
            name="uq_radar_profile_version_tenant_profile_version",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_version_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_id"],
            ["radar_search_profile.tenant_id", "radar_search_profile.id"],
            name="fk_radar_profile_version_profile",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version >= 1", name="ck_radar_profile_version_version"),
        CheckConstraint("freshness_seconds >= 1", name="ck_radar_profile_version_freshness"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_schema_version: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="1"
    )
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    freshness_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("120")
    )
    normalizer_version: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="1"
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RadarSearchRule(Base):
    __tablename__ = "radar_search_rule"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "profile_version_id",
            "rule_key",
            name="uq_radar_search_rule_tenant_version_key",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_search_rule_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_search_rule_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint("kind IN ('include', 'exclude')", name="ck_radar_search_rule_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    expression: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    weight: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RadarProfileSource(Base):
    __tablename__ = "radar_profile_source"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_source_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_profile_source_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_id"],
            ["radar_source.tenant_id", "radar_source.id"],
            name="fk_radar_profile_source_source",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_radar_profile_source_tenant_source_version",
            "tenant_id",
            "source_id",
            "profile_version_id",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class RadarProfileDestination(Base):
    __tablename__ = "radar_profile_destination"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_destination_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_profile_destination_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "destination_id"],
            ["radar_destination.tenant_id", "radar_destination.id"],
            name="fk_radar_profile_destination_destination",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_radar_profile_destination_tenant_destination_version",
            "tenant_id",
            "destination_id",
            "profile_version_id",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
