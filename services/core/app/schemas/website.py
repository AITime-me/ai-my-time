from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class WebsiteStartCommand(BaseModel):
    telegram_user_id: str = Field(min_length=1, max_length=32)
    entry_code: str = Field(min_length=1, max_length=160)
    interaction_id: str = Field(min_length=1, max_length=160)
    telegram_first_name: str | None = Field(default=None, max_length=128)
    telegram_last_name: str | None = Field(default=None, max_length=128)
    telegram_username: str | None = Field(default=None, max_length=64)

    @field_validator("telegram_user_id")
    @classmethod
    def telegram_user_id_is_numeric(cls, value: str) -> str:
        if not value.isdecimal():
            raise ValueError("telegram_user_id must be numeric")
        return value


class WebsiteStartResult(BaseModel):
    user_id: uuid.UUID
    touchpoint_id: uuid.UUID | None = None
    created_user: bool
    created_touchpoint: bool
    next_stage: str
