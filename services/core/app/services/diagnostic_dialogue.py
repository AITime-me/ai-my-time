"""Bounded Diagnostic AI flow; conversation content comes from an injected provider."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostic_assets import load_diagnostic_prompt_bundle
from app.models import AttentionItem, ConsultationRequest, DiagnosticReport, DiagnosticSession, DiagnosticTurn, Event, User
from app.schemas.diagnostic_report import RecordDiagnosticReportV2Command
from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.services.diagnostic_generation import DiagnosticConversationInput, DiagnosticConversationProvider
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
    "Запрос на онлайн-консультацию зафиксирован. Повторно нажимать кнопку не нужно: "
    "эксперт AI My Time увидит его в рабочем списке для связи."
)
DIAGNOSTIC_UNAVAILABLE_TEXT = (
    "Ответы сохранены. Сейчас первичный разбор временно недоступен, "
    "поэтому мы не будем выдавать непроверенный результат. Вернёмся к этому шагу после восстановления сервиса."
)
_PRICE_RE = re.compile(r"(?:цен|стоим|бюджет|прайс|тариф|сколько\s+стоит|\bот\s+\d)", re.I)
def _cta_button(session_id: uuid.UUID) -> list[dict[str, str]]:
    return [{"text": "Записаться на онлайн-консультацию", "callback_data": f"diagnostic:consult:{session_id}"}]


class DiagnosticDialogueService:
    """Stores no more than four user clarifications and closes the session deterministically."""

    def __init__(self, session: AsyncSession, provider: DiagnosticConversationProvider | None) -> None:
        self._session = session
        self._provider = provider
        self._outbox = OutboundQueue(session)

    async def open(self, *, diagnostic_session_id: uuid.UUID) -> bool:
        diagnostic = await self._session.get(DiagnosticSession, diagnostic_session_id)
        if diagnostic is None or diagnostic.status not in {"prepared", "diagnostic_active"}:
            return False
        if self._provider is None:
            await self._pause(diagnostic)
            return False
        turns = await self._turns(diagnostic.id)
        if diagnostic.status == "diagnostic_active" and turns:
            return True
        try:
            response = await self._provider.advance(self._input(diagnostic, turns))
        except Exception:  # provider failure must not roll back already accepted lead data
            await self._pause(diagnostic)
            return False
        if response.diagnostic is not None:
            await self._complete(diagnostic, response.diagnostic)
            return True
        question = self._question(response)
        diagnostic.status = "diagnostic_active"
        await self._append(diagnostic.id, "assistant", question)
        await self._message(diagnostic, question, "opening", [])
        return True

    async def receive(self, *, user_id: uuid.UUID, text: str) -> bool:
        diagnostic = await self._active_or_prepared(user_id)
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
        if diagnostic.status == "prepared":
            await self._pause(diagnostic)
            return True
        user_turns = await self._count(diagnostic.id, "user")
        if user_turns >= 4:
            return True
        await self._append(diagnostic.id, "user", cleaned[:2000])
        user_turns += 1
        turns = await self._turns(diagnostic.id)
        if self._provider is None:
            await self._pause(diagnostic)
            return True
        try:
            response = await self._provider.advance(self._input(diagnostic, turns))
        except Exception:  # preserve the just-recorded answer and leave the session resumable
            await self._pause(diagnostic)
            return True
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
        # Serialize repeated deliveries for one result.  A row lock keeps the
        # idempotency decision local to this diagnostic session without making
        # consultation requests globally unique for a user.
        diagnostic = await self._session.scalar(
            select(DiagnosticSession)
            .where(DiagnosticSession.id == diagnostic_session_id)
            .with_for_update()
        )
        if diagnostic is None or diagnostic.user_id != user_id or diagnostic.status != "diagnostic_completed":
            return False
        user = await self._session.get(User, user_id)
        assert user is not None
        existing = await self._session.scalar(
            select(ConsultationRequest).where(
                ConsultationRequest.diagnostic_session_id == diagnostic.id
            )
        )
        if existing is None:
            request = ConsultationRequest(
                user_id=user_id,
                diagnostic_session_id=diagnostic.id,
                status="new",
            )
            self._session.add(request)
            await self._session.flush()
            self._session.add(Event(user_id=user_id, kind="consultation_requested", payload_json={"diagnostic_session_id": str(diagnostic.id)}))
            self._session.add(
                AttentionItem(
                    user_id=user_id,
                    consultation_request_id=request.id,
                    diagnostic_session_id=diagnostic.id,
                    kind="consultation_requested",
                    reason="Пользователь запросил онлайн-консультацию",
                    priority="normal",
                    status="new",
                )
            )
        user.lifecycle_stage = "consultation_requested"
        await self._message(diagnostic, CONSULTATION_CONFIRMATION, "consultation:confirmation", [])
        return True

    async def _active_or_prepared(self, user_id: uuid.UUID) -> DiagnosticSession | None:
        return await self._session.scalar(
            select(DiagnosticSession).where(
                DiagnosticSession.user_id == user_id,
                DiagnosticSession.status.in_(("diagnostic_active", "prepared")),
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

    async def _pause(self, diagnostic: DiagnosticSession) -> None:
        """Keep all answers and turns intact while waiting for a later approved provider recovery."""
        diagnostic.status = "prepared"
        await self._message(diagnostic, DIAGNOSTIC_UNAVAILABLE_TEXT, "provider-unavailable", [])

    async def _complete(self, diagnostic: DiagnosticSession, generated: DiagnosticResultV2) -> None:
        command = RecordDiagnosticReportV2Command(diagnostic_session_id=diagnostic.id, result=generated)
        result = await DiagnosticReportService(self._session).record_v2(command)
        if result.created:
            await self._message(diagnostic, _telegram_report(generated), "result", _cta_button(diagnostic.id))


def _telegram_report(report: DiagnosticResultV2) -> str:
    """Client view contains no internal v2 names and tolerates optional AI/questions."""
    view = report.client_view
    blocks = [
        "Первичный разбор готов.",
        f"Что сейчас происходит\n{view.what_is_happening}",
        f"Где теряется результат\n{view.where_result_is_lost}",
        f"Как это может работать\n{view.future_process}",
        "Что может взять на себя система\n" + "\n".join(f"• {item}" for item in view.system_responsibilities),
    ]
    if view.ai_responsibilities:
        blocks.append("Где может помочь AI\n" + "\n".join(f"• {item}" for item in view.ai_responsibilities))
    blocks.append("Что останется человеку\n" + "\n".join(f"• {item}" for item in view.human_responsibilities))
    if view.open_questions:
        blocks.append("Что ещё важно понять\n" + "\n".join(f"• {item}" for item in view.open_questions))
    return (
        "\n\n".join(blocks) + "\n\n" + CTA_TEXT
    )
