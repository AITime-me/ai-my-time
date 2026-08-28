"""Durable profile-question state machine used by the Telegram Lead Bot."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessProfile, DiagnosticSession, LeadBotSession, User
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.diagnostic import DiagnosticPreparationService
from app.services.diagnostic_dialogue import DiagnosticDialogueService
from app.services.diagnostic_generation import DiagnosticConversationProvider
from app.services.outbox import OutboundQueue
from app.services.profile import ProfileService


@dataclass(frozen=True)
class ProfileStep:
    code: str
    text: str
    options: tuple[str, ...]


PROFILE_STEPS: tuple[ProfileStep, ...] = (
    ProfileStep(
        "business_type",
        "Что является основой вашего бизнеса?",
        (
            "Услуги",
            "Продажа товаров",
            "Производство",
            "Проектные / подрядные работы",
            "Смешанная модель",
            "Другое",
        ),
    ),
    ProfileStep(
        "team_size", "Сколько человек сейчас в вашей команде?", ("1–3", "4–10", "11–30", "Больше 30")
    ),
    ProfileStep(
        "client_flow",
        "Откуда чаще всего приходят новые обращения?",
        ("Звонки", "Мессенджеры", "Соцсети", "Сайт", "Площадки / маркетплейсы", "Другое"),
    ),
    ProfileStep(
        "current_tools",
        "Где вы сейчас записываете и отслеживаете заявки?",
        (
            "В чатах",
            "В таблицах",
            "В CRM",
            "В блокноте / на бумаге",
            "В нескольких местах",
            "Нигде системно",
        ),
    ),
    ProfileStep(
        "primary_pain", "Что сейчас важнее всего перестать терять?", ("Заявки", "Время", "Деньги", "Контроль")
    ),
    ProfileStep(
        "automation_goal",
        "Что хотелось бы изменить в первую очередь?",
        (
            "Быстрее отвечать клиентам",
            "Не забывать вернуться к клиенту",
            "Не терять информацию",
            "Меньше контролировать вручную",
        ),
    ),
)

_STEP_INDEX = {step.code: index for index, step in enumerate(PROFILE_STEPS)}


def _step_payload(step: ProfileStep, flow_version: int) -> dict[str, object]:
    return {
        "kind": "message",
        "text": step.text,
        "buttons": [
            {"text": option, "callback_data": f"profile:v2:{flow_version}:{step.code}:{index}"}
            for index, option in enumerate(step.options)
        ],
    }


class LeadProfileFlow:
    """Stores state before queuing the next prompt; no provider call is made."""

    def __init__(
        self,
        session: AsyncSession,
        diagnostic_provider_factory: Callable[[], DiagnosticConversationProvider | None] | DiagnosticConversationProvider | None = None,
    ) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)
        self._diagnostic_provider_factory = diagnostic_provider_factory

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
        elif await self._restart_legacy_if_needed(flow):
            await self._session.flush()
        if flow.status == "open":
            step = PROFILE_STEPS[_STEP_INDEX[flow.state]]
            await self._outbox.enqueue(
                user_id=user_id,
                channel="telegram_lead",
                payload=_step_payload(step, flow.version),
                dedupe_key=f"profile:{user_id}:v2:{flow.version}:{step.code}:prompt",
            )
        return flow

    async def answer(
        self,
        *,
        user_id: uuid.UUID,
        question_code: str,
        value: str | None = None,
        flow_version: int | None = None,
        option_index: int | None = None,
    ) -> LeadBotSession:
        flow = await self._session.scalar(
            select(LeadBotSession).where(LeadBotSession.user_id == user_id)
        )
        step_index = _STEP_INDEX.get(question_code)
        if (
            flow is None
            or flow.status != "open"
            or flow.state != question_code
            or flow.flow_version != "v2"
            or flow_version != flow.version
            or step_index is None
        ):
            raise ValueError("unexpected profile answer")
        step = PROFILE_STEPS[step_index]
        if option_index is not None:
            if option_index < 0 or option_index >= len(step.options):
                raise ValueError("unsupported profile answer")
            value = step.options[option_index]
        if value not in step.options:
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
            prepared = await DiagnosticPreparationService(self._session).prepare(
                PrepareDiagnosticCommand(user_id=user_id)
            )
            provider = (
                self._diagnostic_provider_factory()
                if callable(self._diagnostic_provider_factory)
                else self._diagnostic_provider_factory
            )
            await DiagnosticDialogueService(self._session, provider).open(
                diagnostic_session_id=prepared.diagnostic_session_id
            )
            return flow
        next_step = PROFILE_STEPS[step_index + 1]
        flow.state = next_step.code
        flow.version += 1
        await self._outbox.enqueue(
            user_id=user_id,
            channel="telegram_lead",
            payload=_step_payload(next_step, flow.version),
            dedupe_key=f"profile:{user_id}:v2:{flow.version}:{next_step.code}:prompt",
        )
        return flow

    async def _restart_legacy_if_needed(self, flow: LeadBotSession) -> bool:
        """Open exactly one fresh v2 run without touching a legacy snapshot."""
        if flow.flow_version != "legacy" or flow.status != "completed":
            return False
        legacy = await self._session.scalar(
            select(DiagnosticSession.id).where(
                DiagnosticSession.user_id == flow.user_id,
                DiagnosticSession.status == "prepared",
            ).limit(1)
        )
        if legacy is None:
            return False
        flow.flow_version = "v2"
        flow.status = "open"
        flow.state = PROFILE_STEPS[0].code
        flow.version += 1
        profile = await self._session.scalar(select(BusinessProfile).where(BusinessProfile.user_id == flow.user_id))
        if profile is not None:
            profile.status = "in_progress"
            profile.completed_at = None
        return True
