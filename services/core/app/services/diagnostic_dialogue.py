"""Bounded Diagnostic AI flow; conversation content comes from an injected provider."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostic_assets import load_diagnostic_prompt_bundle
from app.models import DiagnosticReport, DiagnosticSession, DiagnosticTurn, Event, User
from app.schemas.diagnostic_report import RecordDiagnosticReportCommand
from app.services.diagnostic_generation import DiagnosticConversationInput, DiagnosticConversationProvider, GeneratedDiagnostic
from app.services.diagnostic_report import DiagnosticReportService
from app.services.outbox import OutboundQueue

CTA_TEXT = (
    "По вашим ответам уже видно направление, но точное решение зависит от того, "
    "как сейчас проходят обращения между каналами, сотрудниками и системами. "
    "На онлайн-консультации эксперт AI My Time разберёт этот процесс подробнее и поможет "
    "определить, что имеет смысл автоматизировать в первую очередь."
)
PRICE_REPLY = load_diagnostic_prompt_bundle().price_reply
CONSULTATION_CONFIRMATION = (
    "Запрос на онлайн-консультацию зафиксирован. Эксперт AI My Time увидит его в рабочем списке для связи."
)
_PRICE_RE = re.compile(r"(?:цен|стоим|бюджет|прайс|тариф|сколько\s+стоит|\bот\s+\d)", re.I)
def _cta_button(session_id: uuid.UUID) -> list[dict[str, str]]:
    return [{"text": "Записаться на онлайн-консультацию", "callback_data": f"diagnostic:consult:{session_id}"}]


class DiagnosticDialogueService:
    """Stores no more than four user clarifications and closes the session deterministically."""

    def __init__(self, session: AsyncSession, provider: DiagnosticConversationProvider) -> None:
        self._session = session
        self._provider = provider
        self._outbox = OutboundQueue(session)

    async def open(self, *, diagnostic_session_id: uuid.UUID) -> None:
        diagnostic = await self._session.get(DiagnosticSession, diagnostic_session_id)
        if diagnostic is None or diagnostic.status != "diagnostic_active":
            return
        response = await self._provider.advance(self._input(diagnostic, []))
        question = self._question(response)
        await self._append(diagnostic.id, "assistant", question)
        await self._message(diagnostic, question, "opening", [])

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
        turns = await self._turns(diagnostic.id)
        response = await self._provider.advance(self._input(diagnostic, turns))
        if response.diagnostic is not None:
            await self._complete(diagnostic, response.diagnostic)
            return True
        if user_turns >= 4:
            raise ValueError("diagnostic provider did not complete after four user turns")
        question = self._question(response)
        await self._append(diagnostic.id, "assistant", question)
        await self._message(diagnostic, question, f"question:{user_turns + 1}", [])
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

    async def _turns(self, diagnostic_id: uuid.UUID) -> list[tuple[str, str]]:
        rows = (await self._session.scalars(select(DiagnosticTurn).where(
            DiagnosticTurn.diagnostic_session_id == diagnostic_id
        ).order_by(DiagnosticTurn.turn_index))).all()
        return [(row.actor, row.content) for row in rows]

    @staticmethod
    def _input(diagnostic: DiagnosticSession, turns: list[tuple[str, str]]) -> DiagnosticConversationInput:
        return DiagnosticConversationInput(
            diagnostic_session_id=diagnostic.id,
            user_id=diagnostic.user_id,
            profile_snapshot=diagnostic.input_snapshot_json,
            turns=turns,
        )

    @staticmethod
    def _question(response) -> str:
        if response.question is None or response.diagnostic is not None:
            raise ValueError("diagnostic provider did not return a question")
        return response.question

    async def _message(self, diagnostic: DiagnosticSession, text: str, suffix: str, buttons: list[dict[str, str]]) -> None:
        await self._outbox.enqueue(user_id=diagnostic.user_id, channel="telegram_lead", payload={"kind": "message", "text": text, "buttons": buttons}, dedupe_key=f"diagnostic:{diagnostic.id}:{suffix}")

    async def _complete(self, diagnostic: DiagnosticSession, generated: GeneratedDiagnostic) -> None:
        command = RecordDiagnosticReportCommand(
            diagnostic_session_id=diagnostic.id,
            summary=generated.summary,
            priorities=generated.priorities,
            next_steps=generated.next_steps,
            limitations=generated.limitations,
            role_split=generated.role_split,
        )
        result = await DiagnosticReportService(self._session).record(command)
        if result.created:
            await self._message(diagnostic, _telegram_report(command), "result", _cta_button(diagnostic.id))


def _telegram_report(report: RecordDiagnosticReportCommand) -> str:
    # The report is already validated by the storage boundary; this formatter remains deliberately plain-text.
    summary = report.summary
    priority = report.priorities[0]
    next_step = report.next_steps[0]
    roles = report.role_split
    limitations = report.limitations
    return (
        "Первичный разбор готов.\n\n"
        f"Короткий вывод\n{summary}\n\n"
        f"Приоритет\n• {priority.title}: {priority.reason}\n\n"
        f"Что можно изменить\n• {next_step.title}: {next_step.action}\n\n"
        "Граница решения\n"
        f"• Автоматизация: {roles.automation[0]}\n"
        f"• AI: {roles.ai[0]}\n"
        f"• Человек: {roles.human[0]}\n\n"
        f"Что ещё уточнить\n• {limitations[0]}\n\n"
        + CTA_TEXT
    )
