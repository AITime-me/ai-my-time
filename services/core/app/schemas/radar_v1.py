"""Demand Radar Reader ↔ Core wire contract v1 (DTO only; no persistence)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION_V1: Literal[1] = 1
CONNECTOR_TELEGRAM: Literal["telegram"] = "telegram"

# Reuse the Core internal-body bound already enforced for consultant traffic.
MAX_OBSERVATION_BYTES = 64 * 1024


class RadarPeerType(StrEnum):
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"
    GROUP = "group"
    USER = "user"


class RadarEventKind(StrEnum):
    MESSAGE_UPSERT = "message_upsert"
    MESSAGE_DELETED = "message_deleted"


class RadarOrigin(StrEnum):
    LIVE = "live"
    CATCH_UP = "catch_up"
    RECONCILIATION = "reconciliation"


class RadarContentKind(StrEnum):
    TEXT = "text"
    CAPTION = "caption"
    EMPTY = "empty"


class RadarAuthorType(StrEnum):
    USER = "user"
    BOT = "bot"
    CHANNEL = "channel"
    ANONYMOUS = "anonymous"


class RadarLinkAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class RadarMonitoringCapability(StrEnum):
    REALTIME = "realtime"
    HISTORY_ONLY = "history_only"
    UNVERIFIED = "unverified"


class RadarSourceType(StrEnum):
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"
    GROUP = "group"
    USER = "user"


class RadarConnectionStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"


class RadarAckStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"


class RadarErrorCode(StrEnum):
    CREDENTIAL_INVALID = "credential_invalid"
    SOURCE_FORBIDDEN = "source_forbidden"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    INVALID_CONTRACT = "invalid_contract"
    BACKPRESSURE = "backpressure"
    TEMPORARY_FAILURE = "temporary_failure"


def require_aware_utc(value: datetime, *, field_name: str) -> datetime:
    """Canonicalize to UTC; reject naive datetimes (Core convention)."""
    from datetime import timezone

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def telegram_decimal_id(value: str, *, field_name: str) -> str:
    if not value.isdecimal():
        raise ValueError(f"{field_name} must be a decimal string")
    if value != "0" and value.startswith("0"):
        raise ValueError(f"{field_name} must not have leading zeros")
    return value


def telegram_peer_id(value: str) -> str:
    """Canonical Radar peer_id: unsigned positive decimal raw entity id.

    ``peer_type`` carries entity class. Telethon/Bot marked ids such as
    ``-100…`` (or any signed form) are rejected fail-closed.
    """
    if value.startswith("-") or value.startswith("+"):
        raise ValueError(
            "peer_id must be an unsigned positive decimal raw Telegram entity id; "
            "Telethon marked forms like -100... are forbidden"
        )
    if not value.isdecimal():
        raise ValueError("peer_id must be an unsigned positive decimal string")
    if value == "0" or value.startswith("0"):
        raise ValueError("peer_id must be a positive decimal string without leading zeros")
    return value


class _RadarModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RadarContentV1(_RadarModel):
    """Bounded original text/caption; never a raw Telegram object dump."""

    kind: RadarContentKind
    text: str | None = Field(default=None, max_length=16_000)

    @model_validator(mode="after")
    def _text_matches_kind(self) -> RadarContentV1:
        if self.kind is RadarContentKind.EMPTY:
            if self.text not in (None, ""):
                raise ValueError("empty content must not carry text")
            return self.model_copy(update={"text": None})
        if self.text is None or self.text == "":
            raise ValueError(f"{self.kind} content requires non-empty text")
        return self


class RadarAuthorV1(_RadarModel):
    id: str | None = Field(default=None, min_length=1, max_length=32)
    username: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=256)
    author_type: RadarAuthorType | None = None

    @field_validator("id")
    @classmethod
    def _id_decimal(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return telegram_decimal_id(value, field_name="author.id")


class RadarLinksV1(_RadarModel):
    message_url: str | None = Field(default=None, max_length=512)
    author_url: str | None = Field(default=None, max_length=512)
    message_url_status: RadarLinkAvailability = RadarLinkAvailability.NOT_APPLICABLE
    author_url_status: RadarLinkAvailability = RadarLinkAvailability.NOT_APPLICABLE

    @model_validator(mode="after")
    def _url_status_consistency(self) -> RadarLinksV1:
        if self.message_url is not None and self.message_url_status is not RadarLinkAvailability.AVAILABLE:
            raise ValueError("message_url requires message_url_status=available")
        if self.message_url is None and self.message_url_status is RadarLinkAvailability.AVAILABLE:
            raise ValueError("message_url_status=available requires message_url")
        if self.author_url is not None and self.author_url_status is not RadarLinkAvailability.AVAILABLE:
            raise ValueError("author_url requires author_url_status=available")
        if self.author_url is None and self.author_url_status is RadarLinkAvailability.AVAILABLE:
            raise ValueError("author_url_status=available requires author_url")
        return self


class RadarSourceManifestItemV1(_RadarModel):
    source_id: str = Field(min_length=1, max_length=128)
    connector: Literal["telegram"] = CONNECTOR_TELEGRAM
    peer_type: RadarPeerType
    peer_id: str = Field(
        min_length=1,
        max_length=32,
        pattern=r"^[1-9][0-9]*$",
        description="Unsigned positive raw Telegram entity id; never -100... marked form",
    )
    source_type: RadarSourceType
    activated_at: datetime
    enabled: bool
    approved: bool
    monitoring_capability: RadarMonitoringCapability

    @field_validator("peer_id")
    @classmethod
    def _peer_id(cls, value: str) -> str:
        return telegram_peer_id(value)

    @field_validator("activated_at")
    @classmethod
    def _activated_at(cls, value: datetime) -> datetime:
        return require_aware_utc(value, field_name="activated_at")


class RadarReaderManifestV1(_RadarModel):
    schema_version: Literal[1] = SCHEMA_VERSION_V1
    reader_id: str = Field(min_length=1, max_length=128)
    manifest_version: str = Field(min_length=1, max_length=64)
    issued_at: datetime
    expires_at: datetime
    sources: list[RadarSourceManifestItemV1] = Field(min_length=1, max_length=500)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def _times(cls, value: datetime, info: object) -> datetime:
        field_name = getattr(info, "field_name", "timestamp")
        return require_aware_utc(value, field_name=str(field_name))

    @model_validator(mode="after")
    def _expiry_after_issue(self) -> RadarReaderManifestV1:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        return self


class RadarObservationV1(_RadarModel):
    """Wire observation. Workspace binding is resolved by Core credentials, not this payload."""

    schema_version: Literal[1] = SCHEMA_VERSION_V1
    observation_id: UUID
    source_id: str = Field(min_length=1, max_length=128)
    manifest_version: str = Field(min_length=1, max_length=64)
    connector: Literal["telegram"] = CONNECTOR_TELEGRAM
    peer_type: RadarPeerType
    peer_id: str = Field(
        min_length=1,
        max_length=32,
        pattern=r"^[1-9][0-9]*$",
        description="Unsigned positive raw Telegram entity id; never -100... marked form",
    )
    message_id: str = Field(min_length=1, max_length=32)
    event_kind: RadarEventKind
    published_at: datetime | None = None
    detected_at: datetime
    edited_at: datetime | None = None
    origin: RadarOrigin
    revision_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    content: RadarContentV1 | None = None
    author: RadarAuthorV1 | None = None
    links: RadarLinksV1 | None = None

    @field_validator("peer_id")
    @classmethod
    def _peer_id(cls, value: str) -> str:
        return telegram_peer_id(value)

    @field_validator("message_id")
    @classmethod
    def _message_id(cls, value: str) -> str:
        return telegram_decimal_id(value, field_name="message_id")

    @field_validator("detected_at")
    @classmethod
    def _detected_at(cls, value: datetime) -> datetime:
        return require_aware_utc(value, field_name="detected_at")

    @field_validator("published_at", "edited_at")
    @classmethod
    def _optional_times(cls, value: datetime | None, info: object) -> datetime | None:
        if value is None:
            return None
        field_name = getattr(info, "field_name", "timestamp")
        return require_aware_utc(value, field_name=str(field_name))

    @model_validator(mode="after")
    def _event_semantics(self) -> RadarObservationV1:
        if self.event_kind is RadarEventKind.MESSAGE_UPSERT:
            if self.published_at is None:
                raise ValueError("published_at is required for message_upsert")
            if self.content is None or self.content.kind is RadarContentKind.EMPTY:
                raise ValueError("message_upsert requires non-empty content")
            return self
        # message_deleted: minimal representation — no invented content/author/links.
        if self.content is not None and self.content.kind is not RadarContentKind.EMPTY:
            raise ValueError("message_deleted content must be null or empty")
        if self.author is not None:
            raise ValueError("message_deleted must not carry author")
        if self.links is not None:
            raise ValueError("message_deleted must not carry links")
        return self


class RadarObservationAckV1(_RadarModel):
    """ACK means durable receipt only — not Signal/delivery/match outcomes."""

    schema_version: Literal[1] = SCHEMA_VERSION_V1
    observation_id: UUID
    receipt_id: UUID
    status: RadarAckStatus


class RadarErrorV1(_RadarModel):
    schema_version: Literal[1] = SCHEMA_VERSION_V1
    code: RadarErrorCode
    message: str = Field(min_length=1, max_length=500)
    retry_after_seconds: int | None = Field(default=None, ge=0, le=86_400)
    http_status: Literal[401, 403, 409, 413, 422, 429, 500, 502, 503]


class RadarHeartbeatV1(_RadarModel):
    schema_version: Literal[1] = SCHEMA_VERSION_V1
    reader_id: str = Field(min_length=1, max_length=128)
    applied_manifest_version: str = Field(min_length=1, max_length=64)
    heartbeat_at: datetime
    connection_status: RadarConnectionStatus
    telegram_authorized: bool
    journal_backlog_count: int = Field(ge=0, le=10_000_000)
    status_detail: str | None = Field(default=None, max_length=500)

    @field_validator("heartbeat_at")
    @classmethod
    def _heartbeat_at(cls, value: datetime) -> datetime:
        return require_aware_utc(value, field_name="heartbeat_at")
