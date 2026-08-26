from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class AdminActor(BaseModel):
    user_id: uuid.UUID
    email: str = Field(min_length=3, max_length=320)
    role: str = Field(pattern="^(owner|manager)$")


class AdminSessionResult(BaseModel):
    actor: AdminActor
    session_token: str = Field(min_length=32)
