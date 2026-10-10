"""Admin DTOs for Demand Radar configuration (no secrets)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _RadarAdminModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RadarSourceCreate(_RadarAdminModel):
    peer_type: Literal["channel", "supergroup", "group", "user"]
    peer_id: int = Field(gt=0)
    source_type: Literal["channel", "supergroup", "group", "user"]
    reader_id: uuid.UUID
    username: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=256)
    is_public: bool = False
    is_approved: bool = False
    enabled: bool = True
    monitoring_capability: Literal["realtime", "history_only", "unverified"] = "unverified"
    activated_at: datetime | None = None


class RadarSourcePatch(_RadarAdminModel):
    expected_config_version: int = Field(ge=1)
    reader_id: uuid.UUID | None = None
    username: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=256)
    is_public: bool | None = None
    is_approved: bool | None = None
    enabled: bool | None = None
    monitoring_capability: Literal["realtime", "history_only", "unverified"] | None = None
    activated_at: datetime | None = None


class RadarSourceView(_RadarAdminModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    reader_id: uuid.UUID
    connector: Literal["telegram"]
    peer_type: str
    peer_id: int
    source_type: str
    username: str | None
    title: str | None
    is_public: bool
    is_approved: bool
    enabled: bool
    monitoring_capability: str
    config_version: int
    activated_at: datetime | None
    last_read_at: datetime | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RadarSourceList(_RadarAdminModel):
    items: list[RadarSourceView]
    limit: int
    offset: int


class RadarReaderView(_RadarAdminModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    reader_key: str
    enabled: bool
    credential_key_id: str
    last_heartbeat_at: datetime | None
    connection_status: str | None
    telegram_authorization_status: str | None
    applied_manifest_version: str | None
    journal_backlog: int
    safe_error: str | None
    created_at: datetime
    updated_at: datetime


class RadarReaderList(_RadarAdminModel):
    items: list[RadarReaderView]
    limit: int
    offset: int


class RadarDestinationCreate(_RadarAdminModel):
    bot_binding_key: str = Field(min_length=1, max_length=128)
    chat_id: int
    enabled: bool = True


class RadarDestinationView(_RadarAdminModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    bot_binding_key: str
    chat_id: int
    enabled: bool
    verification_state: str
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RadarDestinationList(_RadarAdminModel):
    items: list[RadarDestinationView]
    limit: int
    offset: int


class RadarProfileCreate(_RadarAdminModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    enabled: bool = True


class RadarProfileView(_RadarAdminModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    enabled: bool
    active_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class RadarProfileList(_RadarAdminModel):
    items: list[RadarProfileView]
    limit: int
    offset: int


class RadarRuleCreate(_RadarAdminModel):
    rule_key: str = Field(min_length=1, max_length=80)
    kind: Literal["include", "exclude"]
    enabled: bool = True
    expression: dict[str, Any] = Field(default_factory=dict)
    weight: int = 0


class RadarProfileVersionCreate(_RadarAdminModel):
    rule_schema_version: str = Field(default="1", min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=80)
    freshness_seconds: int = Field(default=120, ge=1)
    normalizer_version: str = Field(default="1", min_length=1, max_length=32)
    rules: list[RadarRuleCreate] = Field(default_factory=list)
    source_ids: list[uuid.UUID] = Field(default_factory=list)
    destination_ids: list[uuid.UUID] = Field(default_factory=list)


class RadarRuleView(_RadarAdminModel):
    id: uuid.UUID
    rule_key: str
    kind: str
    enabled: bool
    expression: dict[str, Any]
    weight: int


class RadarProfileVersionView(_RadarAdminModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    profile_id: uuid.UUID
    version: int
    rule_schema_version: str
    category: str | None
    freshness_seconds: int
    normalizer_version: str
    activated_at: datetime | None
    created_at: datetime
    rules: list[RadarRuleView]
    source_ids: list[uuid.UUID]
    destination_ids: list[uuid.UUID]


class RadarProfileActivate(_RadarAdminModel):
    version_id: uuid.UUID
