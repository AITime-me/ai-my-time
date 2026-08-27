"""Bounded local Diagnostic AI MVP flow; no external model or provider is used here."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticReport, DiagnosticSession, DiagnosticTurn, Event, User
from app.schemas.diagnostic_report import RecordDiagnosticReportCommand
from app.services.diagnostic_report import DiagnosticReportService
from app.services.outbox import OutboundQueue

CTA_TEXT = (
    "По вашим ответам уже видно направление, но точное решение зависит от того, "
    "как сейчас проходят обращения между каналами, сотрудниками и системами. "
    "На онлайн-консультации эксперт AI My Time разберёт этот процесс подробнее и поможет "
    "определить, что имеет смысл автоматизировать в первую очередь."
)
PRICE_REPLY = (
    "Стоимость автоматизации рассчитывается индивидуально: она зависит от процесса, "
    "используемых систем, интеграций и объёма разработки. Точный расчёт можно получить "
    "после уточнения задачи на онлайн-консультации с экспертом."
)
CONSULTATION_CONFIRMATION = (
    "Запрос на онлайн-консультацию зафиксирован. Эксперт AI My Time увидит его в рабочем списке для связи."
)
METHODOLOGY_PROMPT = """Ты проводишь короткую первичную диагностику A.I. My Time.
Опирайся только на ответы пользователя; отделяй факты от гипотез. Ищи AS-IS,
ручной разрыв и осторожный TO-BE. Разделяй обычную автоматизацию, AI и решение
человека. Не выдавай ТЗ, архитектуру, интеграционную схему или полный проект.
Задай 2–4 коротких вопроса и закончи разбором с CTA. Никогда не называй цену,
бюджет, диапазон, "от" или любой ценовой ориентир."""

_PRICE_RE = re.compile(r"(?:цен|стоим|бюджет|прайс|тариф|сколько\s+стоит|\bот\s+\d)", re.I)
_QUESTIONS = (
    "Опишите коротко: что происходит с обращением от первого сообщения до ответа клиенту?",
    "На каком участке команда чаще всего ждёт, забывает или переносит информацию вручную?",
)


def _cta_button(session_id: uuid.UUID) -> list[dict[str, str]]:
    return [{"text": "Записаться на онлайн-консультацию", "callback_data": f"diagnostic:consult:{session_id}"}]


class DiagnosticDialogueService:
    """Stores no more than four user clarifications and closes the session deterministically."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)

    async def open(self, *, diagnostic_session_id: uuid.UUID) -> None:
        diagnostic = await self._session.get(DiagnosticSession, diagnostic_session_id)
        if diagnostic is None or diagnostic.status != "diagnostic_active":
            return
        await self._append(diagnostic.id, "assistant", _QUESTIONS[0])
        await self._message(diagnostic, _QUESTIONS[0], "opening", [])

    async def receive(self, *, user_id: uuid.UUID, text: str) -> bool:
        diagnostic = await self._active(user_id)
        if diagnostic is None:
            completed = await self._session.scalar(
                select(DiagnosticSession).where(
                    DiagnosticSession.user_id == user_id,
                    DiagnosticSession.status == "diagnostic_completed",
                ).order_by(DiagnosticSession.created_at.desc())
            )
            if completed is not None:
                await self._message(completed, CTA_TEXT, "completed:info", _cta_button(completed.id))
                return True
            return False
        cleaned = text.strip()
        if not cleaned:
            return True
        if _PRICE_RE.search(cleaned):
            await self._message(diagnostic, PRICE_REPLY, "price", _cta_button(diagnostic.id))
            return True
        user_turns = await self._count(diagnostic.id, "user")
        if user_turns >= 4:
            return True
        await self._append(diagnostic.id, "user", cleaned[:2000])
        user_turns += 1
        if user_turns < len(_QUESTIONS):
            question = _QUESTIONS[user_turns]
            await self._append(diagnostic.id, "assistant", question)
            await self._message(diagnostic, question, f"question:{user_turns + 1}", [])
            return True
        await self._complete(diagnostic)
        return True

    async def consultation_requested(self, *, user_id: uuid.UUID, diagnostic_session_id: uuid.UUID) -> bool:
        diagnostic = await self._session.get(DiagnosticSession, diagnostic_session_id)
        if diagnostic is None or diagnostic.user_id != user_id or diagnostic.status != "diagnostic_completed":
            return False
        user = await self._session.get(User, user_id)
        assert user is not None
        if user.lifecycle_stage != "consultation_requested":
            user.lifecycle_stage = "consultation_requested"
            self._session.add(Event(user_id=user_id, kind="consultation_requested", payload_json={"diagnostic_session_id": str(diagnostic.id)}))
        await self._message(diagnostic, CONSULTATION_CONFIRMATION, "consultation:confirmation", [])
        return True

    async def _active(self, user_id: uuid.UUID) -> DiagnosticSession | None:
        return await self._session.scalar(
            select(DiagnosticSession).where(
                DiagnosticSession.user_id == user_id, DiagnosticSession.status == "diagnostic_active"
            ).order_by(DiagnosticSession.created_at.desc())
        )

    async def _count(self, diagnostic_id: uuid.UUID, actor: str) -> int:
        value = await self._session.scalar(select(func.count()).select_from(DiagnosticTurn).where(
            DiagnosticTurn.diagnostic_session_id == diagnostic_id, DiagnosticTurn.actor == actor
        ))
        return int(value or 0)

    async def _append(self, diagnostic_id: uuid.UUID, actor: str, content: str) -> None:
        index = await self._session.scalar(select(func.coalesce(func.max(DiagnosticTurn.turn_index), 0)).where(
            DiagnosticTurn.diagnostic_session_id == diagnostic_id
        ))
        self._session.add(DiagnosticTurn(diagnostic_session_id=diagnostic_id, turn_index=int(index or 0) + 1, actor=actor, content=content))

    async def _message(self, diagnostic: DiagnosticSession, text: str, suffix: str, buttons: list[dict[str, str]]) -> None:
        await self._outbox.enqueue(user_id=diagnostic.user_id, channel="telegram_lead", payload={"kind": "message", "text": text, "buttons": buttons}, dedupe_key=f"diagnostic:{diagnostic.id}:{suffix}")

    async def _complete(self, diagnostic: DiagnosticSession) -> None:
        snapshot = diagnostic.input_snapshot_json.get("profile_answers", {})
        answers = snapshot if isinstance(snapshot, dict) else {}
        goal = ((answers.get("automation_goal") or {}) if isinstance(answers.get("automation_goal"), dict) else {}).get("value", "первый приоритет")
        report = await DiagnosticReportService(self._session).record(RecordDiagnosticReportCommand(
            diagnostic_session_id=diagnostic.id,
            summary=f"По ответам видно направление: первым стоит разобрать участок «{goal}» и передачу обращения между каналами и сотрудниками.",
            priorities=[{"title": "Путь обращения", "reason": "Нужна единая точка контроля следующего шага.", "confidence": "medium"}],
            next_steps=[{"title": "Проверить один сценарий", "action": "На консультации восстановить путь одного обращения от первого контакта до результата."}],
            limitations=["Нужно уточнить фактические роли и используемые системы."],
            role_split={"automation": ["Фиксация обращения и следующего шага"], "ai": ["Краткая обработка свободного текста обращений"], "human": ["Решение по нестандартным случаям"]},
        ))
        if report.created:
            await self._message(diagnostic, "Первичный разбор готов.\n\n" + CTA_TEXT, "result", _cta_button(diagnostic.id))
