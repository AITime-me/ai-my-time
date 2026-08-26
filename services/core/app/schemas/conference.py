from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class ConferenceStartCommand(BaseModel):
    """Provider-neutral command emitted after a validated Lead Bot update.

    Telegram tokens, raw update bodies, names, and usernames deliberately do
    not enter this contract. A later Telegram adapter validates that payload
    and supplies the stable numeric account id.
    """

    telegram_user_id: str = Field(min_length=1, max_length=32)
    conference_code: str = Field(default="conference_2026", min_length=1, max_length=80)
    qr_code: str | None = Field(default=None, max_length=160)
    entry_code: str | None = Field(default=None, max_length=160)

    @field_validator("telegram_user_id")
    @classmethod
    def telegram_user_id_is_numeric(cls, value: str) -> str:
        if not value.isdecimal():
            raise ValueError("telegram_user_id must be numeric")
        return value


class ConferenceStartResult(BaseModel):
    user_id: uuid.UUID
    conference_entry_id: uuid.UUID
    created_user: bool
    created_entry: bool
    next_stage: str
