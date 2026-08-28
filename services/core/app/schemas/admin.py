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
