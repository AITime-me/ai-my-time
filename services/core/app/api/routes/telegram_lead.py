"""Narrow Telegram Lead Bot ingress; token setup remains outside this module."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

import uuid

from app.adapters.telegram_lead import (
    ConsultationRequest,
    LifecycleCallback,
    CommunicationCommand,
    DiagnosticText,
    ProfileAnswer,
    StartProfile,
    adapt_telegram_lead_payload,
)
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import ConsultationRequest as ConsultationRequestModel, DiagnosticSession, Event, User, UserIdentity
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.lead_profile_flow import LeadProfileFlow
from app.services.diagnostic_acceptance import DiagnosticAcceptanceService, is_acceptance_start
from app.services.diagnostic_dialogue import DiagnosticDialogueService
from app.services.communication import CommunicationConsentService
from app.services.consultation_lifecycle import ConsultationLifecycleService
from app.services.outbox import OutboundQueue
from app.adapters.yandex_diagnostic import build_diagnostic_provider
from app.adapters.telegram_delivery import TelegramCallbackAcknowledger, TelegramDeliveryError, TelegramEdgeCallbackAcknowledger

router = APIRouter(tags=["telegram-lead"])
_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_LOG = logging.getLogger(__name__)


@router.post("/webhooks/telegram/lead", status_code=204)
async def receive_lead_update(payload: dict[str, object], request: Request) -> Response:
    expected_secret = request.app.state.settings.telegram_lead_webhook_secret
    supplied_secret = request.headers.get(_SECRET_HEADER)
    if request.app.state.settings.telegram_transport_mode == "edge":
        edge_secret = request.app.state.settings.telegram_edge_inbound_secret
        if not edge_secret or not hmac.compare_digest(request.headers.get("X-Aimytime-Edge-Auth", ""), edge_secret): raise HTTPException(status_code=401, detail="unauthorized")
    else:
        if not expected_secret: raise HTTPException(status_code=503, detail="lead webhook is not configured")
        if not supplied_secret or not hmac.compare_digest(supplied_secret, expected_secret): raise HTTPException(status_code=401, detail="unauthorized")

    update = adapt_telegram_lead_payload(payload)
    if update is None:
        return Response(status_code=204)

    if isinstance(update, (ProfileAnswer, ConsultationRequest, LifecycleCallback)):
        # Acknowledge the button before any database/provider work so Telegram
        # closes its spinner immediately.  This is UX-only: a transient Bot API
        # failure must never discard a durable profile answer or CTA request.
        await _acknowledge_callback(request, update.callback_query_id)

    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        if isinstance(update, StartProfile):
            # An acceptance link is a closed internal path. Validate it against
            # an existing identity before normal /start handling, so a leaked,
            # expired or foreign link cannot create any lead-side records.
            if is_acceptance_start(update.entry_code):
                user_id = await session.scalar(
                    select(UserIdentity.user_id).where(
                        UserIdentity.provider == "telegram",
                        UserIdentity.connection_scope == "ai_my_time_lead_bot",
                        UserIdentity.external_id == update.telegram_user_id,
                    )
                )
                if user_id is not None:
                    await DiagnosticAcceptanceService(session).consume_and_restart(
                        user_id=user_id,
                        entry_code=update.entry_code,
                    )
                return Response(status_code=204)
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(
                    telegram_user_id=update.telegram_user_id,
                    qr_code=update.entry_code,
                    entry_code=update.entry_code,
                    telegram_first_name=update.telegram_first_name,
                    telegram_last_name=update.telegram_last_name,
                    telegram_username=update.telegram_username,
                )
            )
            completed = await session.scalar(select(DiagnosticSession).where(DiagnosticSession.user_id == entry.user_id, DiagnosticSession.status == "diagnostic_completed").limit(1))
            active = await session.scalar(select(DiagnosticSession).where(DiagnosticSession.user_id == entry.user_id, DiagnosticSession.status.in_(("prepared", "diagnostic_active"))).limit(1))
            if active is not None:
                await OutboundQueue(session).enqueue(user_id=entry.user_id, channel="telegram_lead", payload={"kind":"message","text":"Диагностика ещё не завершена.","buttons":[{"text":"Продолжить диагностику","callback_data":f"diagnostic:resume:{active.id}"}]}, dedupe_key=f"diagnostic:{active.id}:resume-cta")
            elif completed is not None:
                await ConsultationLifecycleService(session).bridge(user_id=entry.user_id)
            else:
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
        user = await session.get(User, user_id)
        if user is None:
            return Response(status_code=204)
        _apply_telegram_profile(user, update)
        if isinstance(update, LifecycleCallback):
            try: entity_id = uuid.UUID(update.entity_id)
            except ValueError: return Response(status_code=204)
            lifecycle = ConsultationLifecycleService(session)
            if update.action == "diagnostic:resume":
                await DiagnosticDialogueService(session, _diagnostic_provider(request)).open(diagnostic_session_id=entity_id)
            elif update.action == "diagnostic:result":
                await lifecycle.replay_result(user_id=user_id, diagnostic_id=entity_id)
            elif update.action == "diagnostic:repeat":
                user.lifecycle_stage = f"repeat_task_input:{entity_id}"
                await OutboundQueue(session).enqueue(user_id=user_id, channel="telegram_lead", payload={"kind":"message","text":"Коротко опишите, что сейчас хочется изменить или наладить в работе бизнеса. Достаточно 1–2 предложений — задача будет передана эксперту AI My Time.","buttons":[]}, dedupe_key=f"diagnostic:{entity_id}:repeat-prompt")
            elif update.action == "diagnostic:channel":
                session.add(Event(user_id=user_id, kind="channel_clicked", payload_json={"diagnostic_session_id": str(entity_id)}))
            else:
                request_row = await session.get(ConsultationRequestModel, entity_id)
                if request_row is not None and request_row.user_id == user_id:
                    if update.action == "consult:confirm": await lifecycle.confirm(request_row, source="client")
                    elif update.action == "consult:reschedule": await lifecycle.reschedule_requested(request_row)
                    elif update.action == "consult:cancel":
                        await OutboundQueue(session).enqueue(user_id=user_id, channel="telegram_lead", payload={"kind":"message","text":"Точно отменить консультацию?","buttons":[{"text":"Да, отменить","callback_data":f"consult:cancel_yes:{request_row.id}"},{"text":"Нет, оставить","callback_data":f"consult:cancel_no:{request_row.id}"}]}, dedupe_key=f"appointment:{request_row.id}:cancel-confirm")
                    elif update.action == "consult:cancel_yes": await lifecycle.cancel(request_row)
            return Response(status_code=204)
        if isinstance(update, DiagnosticText):
            if user.lifecycle_stage.startswith("repeat_task_input:"):
                try: diagnostic_id = uuid.UUID(user.lifecycle_stage.split(":", 1)[1])
                except ValueError: return Response(status_code=204)
                await ConsultationLifecycleService(session).create_repeat(user_id=user_id, diagnostic_id=diagnostic_id, text=update.text)
                user.lifecycle_stage = "consultation_requested"
                return Response(status_code=204)
            await DiagnosticDialogueService(session, _diagnostic_provider(request)).receive(user_id=user_id, text=update.text)
            return Response(status_code=204)
        if isinstance(update, CommunicationCommand):
            await CommunicationConsentService(session).set_status(
                user_id=user_id,
                status="unsubscribed" if update.action == "unsubscribe" else "subscribed",
            )
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
                flow_version=update.flow_version,
                option_index=update.option_index,
            )
        except ValueError:
            return Response(status_code=204)
    return Response(status_code=204)


def _apply_telegram_profile(user: User, update: object) -> None:
    """Telegram sends mutable profile fields with every normal private interaction."""
    user.telegram_first_name = getattr(update, "telegram_first_name", None)
    user.telegram_last_name = getattr(update, "telegram_last_name", None)
    user.telegram_username = getattr(update, "telegram_username", None)
    display_name = " ".join(
        part.strip()
        for part in (user.telegram_first_name or "", user.telegram_last_name or "")
        if part.strip()
    )
    if display_name:
        user.display_name = display_name


def _diagnostic_provider(request: Request):
    factory = getattr(request.app.state, "diagnostic_provider_factory", None)
    if factory is not None:
        return factory()
    try:
        return build_diagnostic_provider(request.app.state.settings)
    except RuntimeError:
        return None


async def _acknowledge_callback(request: Request, callback_query_id: str) -> None:
    factory = getattr(request.app.state, "telegram_callback_acknowledger_factory", None)
    settings = request.app.state.settings
    token = settings.telegram_bot_token
    if factory is None and settings.telegram_transport_mode == "edge" and not (settings.telegram_edge_url and settings.telegram_edge_core_secret):
        _LOG.warning("Telegram callback acknowledgement is unavailable")
        return
    if factory is None and settings.telegram_transport_mode != "edge" and not token:
        _LOG.warning("Telegram callback acknowledgement is unavailable")
        return
    try:
        acknowledger = factory() if factory is not None else (TelegramEdgeCallbackAcknowledger(edge_url=settings.telegram_edge_url or "", secret=settings.telegram_edge_core_secret or "") if settings.telegram_transport_mode == "edge" else TelegramCallbackAcknowledger(token=token or ""))
        await acknowledger.acknowledge(callback_query_id)
    except (TelegramDeliveryError, ValueError, OSError):
        _LOG.warning("Telegram callback acknowledgement failed")
