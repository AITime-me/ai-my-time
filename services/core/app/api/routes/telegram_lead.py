"""Narrow Telegram Lead Bot ingress; token setup remains outside this module."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

import uuid

from app.adapters.telegram_lead import (
    ConsultationRequest,
    DiagnosticText,
    ProfileAnswer,
    StartProfile,
    adapt_telegram_lead_payload,
)
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import UserIdentity
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.lead_profile_flow import LeadProfileFlow
from app.services.diagnostic_dialogue import DiagnosticDialogueService
from app.adapters.yandex_diagnostic import build_diagnostic_provider

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

        user_id = await session.scalar(
            select(UserIdentity.user_id).where(
                UserIdentity.provider == "telegram",
                UserIdentity.connection_scope == "ai_my_time_lead_bot",
                UserIdentity.external_id == update.telegram_user_id,
            )
        )
        if user_id is None:
            return Response(status_code=204)
        if isinstance(update, DiagnosticText):
            await DiagnosticDialogueService(session, _diagnostic_provider(request)).receive(user_id=user_id, text=update.text)
            return Response(status_code=204)
        if isinstance(update, ConsultationRequest):
            try:
                diagnostic_session_id = uuid.UUID(update.diagnostic_session_id)
            except ValueError:
                return Response(status_code=204)
            await DiagnosticDialogueService(session, _diagnostic_provider(request)).consultation_requested(
                user_id=user_id, diagnostic_session_id=diagnostic_session_id
            )
            return Response(status_code=204)
        assert isinstance(update, ProfileAnswer)
        try:
            await LeadProfileFlow(session, diagnostic_provider_factory=lambda: _diagnostic_provider(request)).answer(
                user_id=user_id,
                question_code=update.question_code,
                value=update.value,
            )
        except ValueError:
            return Response(status_code=204)
    return Response(status_code=204)


def _diagnostic_provider(request: Request):
    factory = getattr(request.app.state, "diagnostic_provider_factory", None)
    if factory is not None:
        return factory()
    try:
        return build_diagnostic_provider(request.app.state.settings)
    except RuntimeError:
        return None
