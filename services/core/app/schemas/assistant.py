from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PublicConversationCreate(BaseModel):
    channel: str = Field(pattern="^web$")


class PublicConversationCreated(BaseModel):
    conversation_id: uuid.UUID
    session_token: str


class PublicAssistantMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)


class PublicIntakeCreate(BaseModel):
    kind: str = Field(min_length=2, max_length=80)
    summary: str | None = Field(default=None, max_length=512)
    details_json: dict[str, object] = Field(default_factory=dict)
    consent_record_id: uuid.UUID | None = None


class AssistantProfileDraft(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=256)
    config_json: dict[str, object]


class AssistantBindingUpdate(BaseModel):
    profile_id: uuid.UUID
    is_active: bool = False
    settings_json: dict[str, object] = Field(default_factory=dict)


class AssistantConversationView(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str
    status: str
    last_activity_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class IntakeView(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    assistant_conversation_id: uuid.UUID | None
    channel: str
    kind: str
    state: str
    summary: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
