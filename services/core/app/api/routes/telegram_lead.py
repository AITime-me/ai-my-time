"""Narrow Telegram Lead Bot ingress; token setup remains outside this module."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.adapters.telegram_lead import ProfileAnswer, StartProfile, adapt_telegram_lead_payload
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import UserIdentity
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.lead_profile_flow import LeadProfileFlow

router = APIRouter(tags=["telegram-lead"])
_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@router.post("/webhooks/telegram/lead", status_code=204)
async def receive_lead_update(payload: dict[str, object], request: Request) -> Response:
    expected_secret = request.app.state.settings.telegram_lead_webhook_secret
    supplied_secret = request.headers.get(_SECRET_HEADER)
    if not expected_secret:
        raise HTTPException(status_code=503, detail="lead webhook is not configured")
    if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    update = adapt_telegram_lead_payload(payload)
    if update is None:
        return Response(status_code=204)

    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        if isinstance(update, StartProfile):
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(
                    telegram_user_id=update.telegram_user_id,
                    qr_code=update.entry_code,
                    entry_code=update.entry_code,
                )
            )
            await LeadProfileFlow(session).start(user_id=entry.user_id)
            return Response(status_code=204)

        assert isinstance(update, ProfileAnswer)
        user_id = await session.scalar(
            select(UserIdentity.user_id).where(
                UserIdentity.provider == "telegram",
                UserIdentity.connection_scope == "ai_my_time_lead_bot",
                UserIdentity.external_id == update.telegram_user_id,
            )
        )
        if user_id is None:
            return Response(status_code=204)
        try:
            await LeadProfileFlow(session).answer(
                user_id=user_id,
                question_code=update.question_code,
                value=update.value,
            )
        except ValueError:
            return Response(status_code=204)
    return Response(status_code=204)
