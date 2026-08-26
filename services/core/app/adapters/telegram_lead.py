"""Translate a bounded Telegram update payload into local Lead Bot inputs."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError


class _Chat(BaseModel):
    type: str


class _Sender(BaseModel):
    id: int


class _Message(BaseModel):
    chat: _Chat
    from_: _Sender | None = Field(default=None, alias="from")
    text: str | None = None


class _CallbackQuery(BaseModel):
    from_: _Sender = Field(alias="from")
    message: _Message | None = None
    data: str | None = None


class _Update(BaseModel):
    message: _Message | None = None
    callback_query: _CallbackQuery | None = None


@dataclass(frozen=True)
class StartProfile:
    telegram_user_id: str
    entry_code: str


@dataclass(frozen=True)
class ProfileAnswer:
    telegram_user_id: str
    question_code: str
    value: str


TelegramLeadInput = StartProfile | ProfileAnswer


def adapt_telegram_lead_payload(payload: object) -> TelegramLeadInput | None:
    """Return a recognised private-chat action, otherwise ignore the update.

    Telegram may send update types this MVP does not use.  Invalid or unrelated
    payloads are deliberately non-actions so the webhook can acknowledge them
    without exposing a provider parser as an application contract.
    """
    try:
        update = _Update.model_validate(payload)
    except ValidationError:
        return None

    message = update.message
    if (
        message is not None
        and message.chat.type == "private"
        and message.from_ is not None
        and message.text is not None
    ):
        entry_code = _start_parameter(message.text)
        if entry_code is not None:
            return StartProfile(
                telegram_user_id=str(message.from_.id), entry_code=entry_code
            )

    callback = update.callback_query
    if (
        callback is None
        or callback.message is None
        or callback.message.chat.type != "private"
        or callback.data is None
    ):
        return None
    parsed = _profile_callback(callback.data)
    if parsed is None:
        return None
    return ProfileAnswer(
        telegram_user_id=str(callback.from_.id),
        question_code=parsed[0],
        value=parsed[1],
    )


def _start_parameter(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if not parts or parts[0] != "/start":
        return None
    return parts[1].strip() if len(parts) == 2 else "telegram_direct"


def _profile_callback(data: str) -> tuple[str, str] | None:
    prefix, separator, remainder = data.partition(":")
    if prefix != "profile" or not separator:
        return None
    question_code, separator, value = remainder.partition(":")
    if not question_code or not separator or not value:
        return None
    return question_code, value
