"""The bounded consultation lifecycle and client callback behaviours."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttentionItem, ConsultationRequest, DiagnosticReport, DiagnosticSession, Event, User
from app.core.timezones import format_moscow
from app.services.outbox import OutboundQueue
from app.services.scheduled_events import ScheduledEventService, _appointment_buttons
from app.core.telegram_channel import channel_callback_button
from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.services.diagnostic_result_rendering import (
    render_legacy_telegram_diagnostic_result,
    render_telegram_diagnostic_result,
)

ACTIVE = {"new", "waiting_response", "scheduled"}
TERMINAL = {"completed", "cancelled", "no_show"}
THANK_YOU = "Спасибо за консультацию AI My Time. Если появится новая задача, вы всегда можете вернуться к нам."


class ConsultationLifecycleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session; self._outbox = OutboundQueue(session); self._schedule = ScheduledEventService(session)

    async def active(self, user_id: uuid.UUID) -> ConsultationRequest | None:
        return await self._session.scalar(select(ConsultationRequest).where(
            ConsultationRequest.user_id == user_id, ConsultationRequest.status.in_(ACTIVE)
        ).order_by(ConsultationRequest.created_at.desc()).limit(1))

    async def create_repeat(self, *, user_id: uuid.UUID, diagnostic_id: uuid.UUID, text: str) -> ConsultationRequest | None:
        diagnostic = await self._session.scalar(
            select(DiagnosticSession).where(DiagnosticSession.id == diagnostic_id).with_for_update()
        )
        if diagnostic is None or diagnostic.user_id != user_id or diagnostic.status != "diagnostic_completed":
            return None
        if not text.strip() or await self.active(user_id): return None
        request = ConsultationRequest(user_id=user_id, diagnostic_session_id=diagnostic_id, status="new", origin_type="repeat_task", repeat_task_text=text.strip())
        self._session.add(request); await self._session.flush()
        self._session.add(Event(user_id=user_id, kind="repeat_consultation_requested", payload_json={"consultation_request_id":str(request.id)}))
        self._session.add(AttentionItem(user_id=user_id, consultation_request_id=request.id, diagnostic_session_id=diagnostic_id, kind="repeat_consultation_requested", reason="Повторное обращение — новая задача", priority="normal", status="new"))
        await self._outbox.enqueue(user_id=user_id, channel="telegram_lead", payload={"kind":"message","text":"Задача получена. Эксперт AI My Time свяжется с вами в Telegram в рабочее время.","buttons":[]}, dedupe_key=f"repeat-consultation:{request.id}:confirmation")
        return request

    async def schedule_appointment(self, request: ConsultationRequest, *, appointment_at: datetime, owner_confirm: bool = False) -> ConsultationRequest:
        if appointment_at.tzinfo is None: raise ValueError("appointment_at must be timezone-aware")
        if request.status not in ACTIVE: raise ValueError("consultation is closed")
        request.status = "scheduled"; request.appointment_at = appointment_at
        user = await self._session.get(User, request.user_id)
        if user is not None:
            user.lifecycle_stage = "consultation_scheduled"
        request.reschedule_requested_at = None
        if owner_confirm:
            request.confirmation_state = "confirmed"; request.confirmed_at = datetime.now(timezone.utc); request.confirmation_source = "owner"
        else:
            request.confirmation_state = "pending"; request.confirmed_at = None; request.confirmation_source = None
        await self._schedule.appointment_events(request)
        await self._outbox.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message", "text":f"Консультация назначена на {format_moscow(appointment_at)}. Подтвердите, перенесите или отмените встречу.", "buttons":_appointment_buttons(request.id)}, dedupe_key=f"appointment:{request.id}:{appointment_at.isoformat()}:notice")
        return request

    async def confirm(self, request: ConsultationRequest, *, source: str) -> ConsultationRequest:
        if request.status != "scheduled": return request
        if request.confirmation_state != "confirmed":
            request.confirmation_state="confirmed"; request.confirmed_at=datetime.now(timezone.utc); request.confirmation_source=source
            await self._schedule.cancel_for_consultation(request.id)
            if request.appointment_at: await self._schedule.appointment_events(request)
            await self._outbox.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message","text":"Встреча подтверждена. Напомним заранее.","buttons":[]}, dedupe_key=f"appointment:{request.id}:confirmed")
        return request

    async def reschedule_requested(self, request: ConsultationRequest) -> ConsultationRequest:
        if request.status != "scheduled": return request
        request.reschedule_requested_at=datetime.now(timezone.utc); await self._schedule.cancel_for_consultation(request.id)
        await self._outbox.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message","text":"Эксперт свяжется с вами, чтобы подобрать новое время.","buttons":[]}, dedupe_key=f"appointment:{request.id}:reschedule-request")
        return request

    async def cancel(self, request: ConsultationRequest, *, notify: bool = True) -> ConsultationRequest:
        if request.status not in TERMINAL:
            request.status="cancelled"; await self._schedule.cancel_for_consultation(request.id)
            user = await self._session.get(User, request.user_id)
            if user is not None:
                user.lifecycle_stage = "consultation_cancelled"
            if notify: await self._outbox.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message","text":"Консультация отменена.","buttons":[]}, dedupe_key=f"appointment:{request.id}:cancelled")
        return request

    async def complete(self, request: ConsultationRequest, *, status: str) -> ConsultationRequest:
        if status not in {"completed", "no_show", "cancelled"}: raise ValueError("unsupported terminal status")
        request.status=status; await self._schedule.cancel_for_consultation(request.id)
        user = await self._session.get(User, request.user_id)
        if user is not None:
            user.lifecycle_stage = f"consultation_{status}"
        if status == "completed": await self._outbox.enqueue(user_id=request.user_id, channel="telegram_lead", payload={"kind":"message","text":THANK_YOU,"buttons":[]}, dedupe_key=f"consultation:{request.id}:thank-you")
        return request

    async def bridge(self, *, user_id: uuid.UUID) -> bool:
        diagnostic = await self._session.scalar(select(DiagnosticSession).where(DiagnosticSession.user_id==user_id, DiagnosticSession.status=="diagnostic_completed").order_by(DiagnosticSession.created_at.desc()).limit(1))
        if diagnostic is None or await self.active(user_id): return False
        buttons = [
            {"text":"Посмотреть прошлый результат","callback_data":f"diagnostic:result:{diagnostic.id}"},
            {"text":"Разобрать новую задачу с экспертом","callback_data":f"diagnostic:repeat:{diagnostic.id}"},
        ]
        if button := channel_callback_button(diagnostic.id):
            buttons.append(button)
        await self._outbox.enqueue(user_id=user_id, channel="telegram_lead", payload={"kind":"message", "text":"Вы уже проходили диагностику AI My Time — её результат сохранён. Если с тех пор появилась другая задача, её можно передать эксперту на разбор.", "buttons":buttons}, dedupe_key=f"diagnostic:{diagnostic.id}:bridge")
        return True

    async def replay_result(self, *, user_id: uuid.UUID, diagnostic_id: uuid.UUID) -> bool:
        report = await self._session.scalar(select(DiagnosticReport).join(DiagnosticSession).where(DiagnosticReport.diagnostic_session_id==diagnostic_id, DiagnosticSession.user_id==user_id))
        if report is None: return False
        if report.result_version == "v2":
            try:
                text = render_telegram_diagnostic_result(DiagnosticResultV2.model_validate(report.result_json))
            except ValueError:
                return False
        else:
            text = render_legacy_telegram_diagnostic_result(
                summary=report.summary,
                priorities=report.priorities_json,
                next_steps=report.next_steps_json,
                role_split=report.role_split_json,
                limitations=report.limitations_json,
            )
        await self._outbox.enqueue(user_id=user_id, channel="telegram_lead", payload={"kind":"message","text":text,"buttons":[]}, dedupe_key=f"diagnostic:{diagnostic_id}:result-replay")
        return True
