"""Minimal durable model for the conference path.

This deliberately holds no studio, booking, amoCRM, or provider-secret data.
Telegram's stable numeric user id is an identity link; a Telegram username is
mutable and remains an event/profile attribute, not the primary key.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Timestamped, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lifecycle_stage: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="new"
    )


class UserIdentity(Timestamped, Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider", "connection_scope", "external_id",
            name="uq_user_identities_provider_scope_external_id",
        ),
        Index("ix_user_identities_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    connection_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)


class AdminUser(Timestamped, Base):
    """Human operator account, intentionally separate from Telegram leads."""

    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AdminSession(Base):
    """Only the digest is durable; a raw session token is never stored."""

    __tablename__ = "admin_sessions"
    __table_args__ = (Index("ix_admin_sessions_user_expires", "admin_user_id", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LeadBotSession(Timestamped, Base):
    """Durable state of the Lead Bot profile flow for one internal user."""

    __tablename__ = "lead_bot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    state: Mapped[str] = mapped_column(String(80), nullable=False, server_default="business_type")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
    # Rows present before Diagnostic AI v2 are explicitly marked by the
    # migration as legacy. A new v2 profile flow is allowed to replace only
    # that lead-flow projection; its historical diagnostic snapshot remains.
    flow_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="v2")


class OutboundMessage(Base):
    """Provider-neutral outbox with a short delivery lease for each worker."""

    __tablename__ = "outbound_messages"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_outbound_messages_dedupe_key"),
        Index("ix_outbound_messages_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    attempt_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Touchpoint(Base):
    __tablename__ = "touchpoints"
    __table_args__ = (
        Index("ix_touchpoints_user_observed_at", "user_id", "observed_at"),
        Index("ix_touchpoints_source_code", "source_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    source_code: Mapped[str] = mapped_column(String(80), nullable=False)
    entry_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )


class BusinessProfile(Timestamped, Base):
    """Current state projection of profile completion, without personal data."""

    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="in_progress"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProfileAnswer(Base):
    """Versioned answer: later edits preserve a concise change history."""

    __tablename__ = "profile_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_code", "revision", name="uq_profile_answers_revision"),
        Index("ix_profile_answers_user_question", "user_id", "question_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    question_code: Mapped[str] = mapped_column(String(80), nullable=False)
    answer_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(nullable=False, server_default="1")
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DiagnosticSession(Timestamped, Base):
    """One reproducible diagnostic run using a snapshot of profile answers."""

    __tablename__ = "diagnostic_sessions"
    __table_args__ = (Index("ix_diagnostic_sessions_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="prepared"
    )
    input_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiagnosticReport(Timestamped, Base):
    """Structured result, intentionally separate from raw model/provider output."""

    __tablename__ = "diagnostic_reports"
    __table_args__ = (UniqueConstraint("diagnostic_session_id", name="uq_diagnostic_reports_session"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priorities_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False)
    next_steps_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False)
    limitations_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False)
    role_split_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    result_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="v1")
    result_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default="{}")


class DiagnosticTurn(Base):
    """A bounded, auditable diagnostic conversation, separate from the profile snapshot."""

    __tablename__ = "diagnostic_turns"
    __table_args__ = (
        UniqueConstraint("diagnostic_session_id", "turn_index", name="uq_diagnostic_turns_session_index"),
        Index("ix_diagnostic_turns_session_index", "diagnostic_session_id", "turn_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    turn_index: Mapped[int] = mapped_column(nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_user_occurred_at", "user_id", "occurred_at"),
        Index("ix_events_kind_occurred_at", "kind", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )


class ConferenceEntry(Timestamped, Base):
    __tablename__ = "conference_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "conference_code", name="uq_conference_entries_user_code"),
        Index("ix_conference_entries_code_created_at", "conference_code", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    conference_code: Mapped[str] = mapped_column(String(80), nullable=False)
    qr_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="started"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
