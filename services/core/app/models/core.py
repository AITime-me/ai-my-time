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
