"""Durable profile-question state machine used by the Telegram Lead Bot."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LeadBotSession, User
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.diagnostic import DiagnosticPreparationService
from app.services.outbox import OutboundQueue
from app.services.profile import ProfileService


@dataclass(frozen=True)
class ProfileStep:
    code: str
    text: str
    options: tuple[str, ...]


PROFILE_STEPS: tuple[ProfileStep, ...] = (
    ProfileStep("business_type", "Чем занимается ваш бизнес?", ("Автосервис", "Магазин", "Услуги", "Другое")),
    ProfileStep("team_size", "Сколько человек в команде?", ("1–3", "4–10", "11–30", "Больше 30")),
    ProfileStep("client_flow", "Откуда чаще приходят обращения?", ("Звонки", "Telegram", "Соцсети", "Сайт")),
    ProfileStep("current_tools", "Где сейчас живут заявки?", ("Чаты", "Таблица", "CRM", "Везде понемногу")),
    ProfileStep("primary_pain", "Что теряется чаще всего?", ("Заявки", "Время", "Статусы", "Контроль")),
    ProfileStep("automation_goal", "Что важнее всего наладить первым?", ("Ответ клиенту", "Следующий шаг", "Контроль команды", "Отчётность")),
)

_STEP_INDEX = {step.code: index for index, step in enumerate(PROFILE_STEPS)}


def _step_payload(step: ProfileStep) -> dict[str, object]:
    return {
        "kind": "message",
        "text": step.text,
        "buttons": [
            {"text": option, "callback_data": f"profile:{step.code}:{option}"}
            for option in step.options
        ],
    }


class LeadProfileFlow:
    """Stores state before queuing the next prompt; no provider call is made."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)

    async def start(self, *, user_id: uuid.UUID) -> LeadBotSession:
        user = await self._session.get(User, user_id)
        if user is None:
            raise ValueError("user not found")
        flow = await self._session.scalar(
            select(LeadBotSession).where(LeadBotSession.user_id == user_id)
        )
        if flow is None:
            flow = LeadBotSession(user_id=user_id, state=PROFILE_STEPS[0].code, status="open")
            self._session.add(flow)
            await self._session.flush()
        if flow.status == "open":
            step = PROFILE_STEPS[_STEP_INDEX[flow.state]]
            await self._outbox.enqueue(
                user_id=user_id,
                channel="telegram_lead",
                payload=_step_payload(step),
                dedupe_key=f"profile:{user_id}:{step.code}:prompt",
            )
        return flow

    async def answer(self, *, user_id: uuid.UUID, question_code: str, value: str) -> LeadBotSession:
        flow = await self._session.scalar(
            select(LeadBotSession).where(LeadBotSession.user_id == user_id)
        )
        if flow is None or flow.status != "open" or flow.state != question_code:
            raise ValueError("unexpected profile answer")
        step_index = _STEP_INDEX.get(question_code)
        if step_index is None:
            raise ValueError("unsupported profile question")
        if value not in PROFILE_STEPS[step_index].options:
            raise ValueError("unsupported profile answer")
        is_last = step_index == len(PROFILE_STEPS) - 1
        await ProfileService(self._session).save(
            SaveProfileAnswersCommand(
                user_id=user_id,
                answers=[{"question_code": question_code, "value": value}],
                complete=is_last,
            )
        )
        if is_last:
            flow.status = "completed"
            flow.state = "complete"
            flow.version += 1
            await DiagnosticPreparationService(self._session).prepare(
                PrepareDiagnosticCommand(user_id=user_id)
            )
            await self._outbox.enqueue(
                user_id=user_id,
                channel="telegram_lead",
                payload={
                    "kind": "message",
                    "text": "Спасибо. Собираю для вас приоритеты и следующий шаг.",
                    "buttons": [],
                },
                dedupe_key=f"profile:{user_id}:complete:message",
            )
            return flow
        next_step = PROFILE_STEPS[step_index + 1]
        flow.state = next_step.code
        flow.version += 1
        await self._outbox.enqueue(
            user_id=user_id,
            channel="telegram_lead",
            payload=_step_payload(next_step),
            dedupe_key=f"profile:{user_id}:{next_step.code}:prompt",
        )
        return flow
