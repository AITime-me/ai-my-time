"""Narrow Telegram Lead Bot ingress; token setup remains outside this module."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import UserIdentity
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.lead_profile_flow import LeadProfileFlow

router = APIRouter(tags=["telegram-lead"])
_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


class TelegramChat(BaseModel):
    type: str


class TelegramSender(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    chat: TelegramChat
    from_: TelegramSender | None = Field(default=None, alias="from")
    text: str | None = None


class TelegramCallbackQuery(BaseModel):
    id: str
    from_: TelegramSender = Field(alias="from")
    message: TelegramMessage | None = None
    data: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None


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


@router.post("/webhooks/telegram/lead", status_code=204)
async def receive_lead_update(update: TelegramUpdate, request: Request) -> Response:
    expected_secret = request.app.state.settings.telegram_lead_webhook_secret
    supplied_secret = request.headers.get(_SECRET_HEADER)
    if not expected_secret:
        raise HTTPException(status_code=503, detail="lead webhook is not configured")
    if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        message = update.message
        if (
            message is not None
            and message.chat.type == "private"
            and message.from_ is not None
            and message.text
        ):
            entry_code = _start_parameter(message.text)
            if entry_code is not None:
                entry = await ConferenceIntakeService(session).start(
                    ConferenceStartCommand(
                        telegram_user_id=str(message.from_.id),
                        qr_code=entry_code,
                        entry_code=entry_code,
                    )
                )
                await LeadProfileFlow(session).start(user_id=entry.user_id)
            return Response(status_code=204)

        callback = update.callback_query
        if (
            callback is None
            or callback.message is None
            or callback.message.chat.type != "private"
            or callback.data is None
        ):
            return Response(status_code=204)
        parsed_callback = _profile_callback(callback.data)
        if parsed_callback is None:
            return Response(status_code=204)
        user_id = await session.scalar(
            select(UserIdentity.user_id).where(
                UserIdentity.provider == "telegram",
                UserIdentity.connection_scope == "ai_my_time_lead_bot",
                UserIdentity.external_id == str(callback.from_.id),
            )
        )
        if user_id is None:
            return Response(status_code=204)
        try:
            await LeadProfileFlow(session).answer(
                user_id=user_id,
                question_code=parsed_callback[0],
                value=parsed_callback[1],
            )
        except ValueError:
            return Response(status_code=204)
    return Response(status_code=204)
