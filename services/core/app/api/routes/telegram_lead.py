"""Narrow Telegram Lead Bot ingress; token setup remains outside this module."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService

router = APIRouter(tags=["telegram-lead"])
_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


class TelegramChat(BaseModel):
    type: str


class TelegramSender(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    chat: TelegramChat
    from_: TelegramSender = Field(alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None


def _start_parameter(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if not parts or parts[0] != "/start":
        return None
    return parts[1].strip() if len(parts) == 2 else "telegram_direct"


@router.post("/webhooks/telegram/lead", status_code=204)
async def receive_lead_update(update: TelegramUpdate, request: Request) -> Response:
    expected_secret = request.app.state.settings.telegram_lead_webhook_secret
    supplied_secret = request.headers.get(_SECRET_HEADER)
    if not expected_secret:
        raise HTTPException(status_code=503, detail="lead webhook is not configured")
    if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    message = update.message
    if message is None or message.chat.type != "private" or not message.text:
        return Response(status_code=204)
    entry_code = _start_parameter(message.text)
    if entry_code is None:
        return Response(status_code=204)

    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        await ConferenceIntakeService(session).start(
            ConferenceStartCommand(
                telegram_user_id=str(message.from_.id),
                qr_code=entry_code,
                entry_code=entry_code,
            )
        )
    return Response(status_code=204)
