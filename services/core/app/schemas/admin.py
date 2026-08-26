from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminLeadView(BaseModel):
    user_id: uuid.UUID
    lifecycle_stage: str
    conference_code: str | None
    diagnostic_status: str | None
    diagnostic_summary: str | None
    created_at: datetime


class AdminLeadList(BaseModel):
    items: list[AdminLeadView]
    limit: int = Field(ge=1, le=100)
