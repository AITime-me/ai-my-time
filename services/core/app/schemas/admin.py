from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminLeadView(BaseModel):
    user_id: uuid.UUID
    display_name: str | None = None
    telegram_username: str | None = None
    lifecycle_stage: str
    source: str | None = None
    conference_code: str | None = None
    diagnostic_status: str | None
    diagnostic_summary: str | None
    consultation_status: str | None
    communication_status: str
    marketing_consent_status: str
    telegram_reachability: str
    attention_count: int = Field(ge=0)
    created_at: datetime
    last_activity_at: datetime | None = None


class AdminLeadList(BaseModel):
    items: list[AdminLeadView]
    limit: int = Field(ge=1, le=100)


class AdminDiagnosticView(BaseModel):
    diagnostic_session_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    summary: str | None = None
    result_version: str | None = None
    result: dict[str, object] | None = None


class AdminConsultationView(BaseModel):
    consultation_request_id: uuid.UUID
    diagnostic_session_id: uuid.UUID
    status: str
    created_at: datetime
    diagnostic_summary: str | None = None
    source: str | None = None


class AdminAttentionView(BaseModel):
    attention_item_id: uuid.UUID
    kind: str
    reason: str
    priority: str
    status: str
    created_at: datetime
    linked_diagnostic_session_id: uuid.UUID | None = None
    consultation_request_id: uuid.UUID | None = None


class AdminPersonDetail(BaseModel):
    person: AdminLeadView
    profile_answers: dict[str, object]
    diagnostics: list[AdminDiagnosticView]
    consultations: list[AdminConsultationView]
    attention_items: list[AdminAttentionView]


class AdminDashboard(BaseModel):
    new_people: int = Field(ge=0)
    started_diagnostics: int = Field(ge=0)
    completed_diagnostics: int = Field(ge=0)
    consultation_requests: int = Field(ge=0)
    attention_items: int = Field(ge=0)
    funnel: dict[str, int]


class AdminConsultationList(BaseModel):
    items: list[AdminConsultationView]


class AdminAttentionList(BaseModel):
    items: list[AdminAttentionView]


class AdminStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=24)


class AdminConsentUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=24)


class AdminKnowledgeDraftCreate(BaseModel):
    namespace: str = Field(min_length=2, max_length=80)
    key: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=256)
    content_json: dict[str, object]
    comment: str | None = Field(default=None, max_length=512)


class AdminKnowledgeVersionView(BaseModel):
    knowledge_version_id: uuid.UUID
    version: int
    status: str
    content_json: dict[str, object]
    comment: str | None = None
    published_at: datetime | None = None
    created_at: datetime


class AdminKnowledgeAssetView(BaseModel):
    knowledge_asset_id: uuid.UUID
    namespace: str
    key: str
    title: str
    published_version_id: uuid.UUID | None = None
    versions: list[AdminKnowledgeVersionView]


class AdminKnowledgeList(BaseModel):
    items: list[AdminKnowledgeAssetView]


class AdminOperationalTraceEvent(BaseModel):
    occurred_at: datetime
    component: str
    event_type: str
    status: str
    diagnostic_session_id: uuid.UUID | None = None
    outbox_message_id: uuid.UUID | None = None


class AdminOperationalTrace(BaseModel):
    user_id: uuid.UUID
    items: list[AdminOperationalTraceEvent]


class AdminSegmentView(BaseModel):
    segment_id: uuid.UUID
    key: str
    title: str
    eligible_count: int = Field(ge=0)


class AdminSegmentList(BaseModel):
    items: list[AdminSegmentView]


class AdminBroadcastDraftCreate(BaseModel):
    segment_id: uuid.UUID
    title: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=2, max_length=4000)


class AdminBroadcastView(BaseModel):
    broadcast_id: uuid.UUID
    segment_id: uuid.UUID
    title: str
    body: str
    status: str
    eligible_count: int = Field(ge=0)
    queued_count: int = Field(ge=0)
    sent_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    created_at: datetime


class AdminBroadcastList(BaseModel):
    items: list[AdminBroadcastView]


class AdminAnalytics(BaseModel):
    period_days: int
    people: int = Field(ge=0)
    diagnostic_started: int = Field(ge=0)
    diagnostic_completed: int = Field(ge=0)
    consultation_requested: int = Field(ge=0)
    completion_rate: float | None = None
    consultation_rate: float | None = None
