"""Bounded local Diagnostic AI MVP flow; no external model or provider is used here."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.diagnostic_assets import load_diagnostic_prompt_bundle
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
PRICE_REPLY = load_diagnostic_prompt_bundle().price_reply
CONSULTATION_CONFIRMATION = (
    "Запрос на онлайн-консультацию зафиксирован. Эксперт AI My Time увидит его в рабочем списке для связи."
)
_PRICE_RE = re.compile(r"(?:цен|стоим|бюджет|прайс|тариф|сколько\s+стоит|\bот\s+\d)", re.I)
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
        question = _opening_question(diagnostic.input_snapshot_json)
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
        if user_turns == 1:
            question = await self._followup_question(diagnostic)
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

    async def _followup_question(self, diagnostic: DiagnosticSession) -> str:
        first_answer = await self._session.scalar(
            select(DiagnosticTurn.content).where(
                DiagnosticTurn.diagnostic_session_id == diagnostic.id,
                DiagnosticTurn.actor == "user",
            ).order_by(DiagnosticTurn.turn_index).limit(1)
        )
        reference = _short_reference(first_answer or "этот процесс")
        pain = _answer_value(diagnostic.input_snapshot_json, "primary_pain")
        return (
            f"Вы описали: «{reference}». На каком участке в этом процессе чаще всего теряется «{pain}» "
            "или сотруднику приходится вручную возвращаться к обращению?"
        )

    async def _message(self, diagnostic: DiagnosticSession, text: str, suffix: str, buttons: list[dict[str, str]]) -> None:
        await self._outbox.enqueue(user_id=diagnostic.user_id, channel="telegram_lead", payload={"kind": "message", "text": text, "buttons": buttons}, dedupe_key=f"diagnostic:{diagnostic.id}:{suffix}")

    async def _complete(self, diagnostic: DiagnosticSession) -> None:
        snapshot = diagnostic.input_snapshot_json
        business = _answer_value(snapshot, "business_type")
        flow = _answer_value(snapshot, "client_flow")
        tools = _answer_value(snapshot, "current_tools")
        pain = _answer_value(snapshot, "primary_pain")
        goal = _answer_value(snapshot, "automation_goal")
        command = RecordDiagnosticReportCommand(
            diagnostic_session_id=diagnostic.id,
            summary=(
                f"Для бизнеса «{business}» обращения чаще приходят через «{flow}», а заявки ведутся «{tools}». "
                f"Гипотеза: при таком пути первым стоит убрать риск потери «{pain}» и поддержать цель «{goal}»."
            ),
            priorities=[{
                "title": f"Сделать следующий шаг по обращению видимым",
                "reason": f"Это снижает риск потери «{pain}» при передаче обращения из «{flow}» в «{tools}».",
                "confidence": "medium",
            }],
            next_steps=[{
                "title": "Зафиксировать один следующий шаг",
                "action": (
                    f"На ближайшую неделю в канале «{flow}» фиксируйте для каждого нового обращения "
                    "ответственного и следующий шаг до передачи коллеге."
                ),
            }],
            limitations=["Нужно уточнить роли сотрудников, фактический порядок передачи и используемые системы."],
            role_split={
                "automation": ["Фиксация обращения, ответственного и следующего шага"],
                "ai": ["Краткое выделение сути свободного текста обращения"],
                "human": ["Решение по нестандартному клиентскому случаю"],
            },
        )
        result = await DiagnosticReportService(self._session).record(command)
        if result.created:
            await self._message(diagnostic, _telegram_report(command), "result", _cta_button(diagnostic.id))


def _answer_value(snapshot: dict[str, object], code: str) -> str:
    answers = snapshot.get("profile_answers", {})
    answer = answers.get(code, {}) if isinstance(answers, dict) else {}
    value = answer.get("value") if isinstance(answer, dict) else None
    return value if isinstance(value, str) and value else "не уточнено"


def _opening_question(snapshot: dict[str, object]) -> str:
    flow = _answer_value(snapshot, "client_flow")
    tools = _answer_value(snapshot, "current_tools")
    if tools in {"В чатах", "В нескольких местах", "Нигде системно"}:
        return (
            f"Когда новое обращение приходит через «{flow}», кто первым его видит и где команда сейчас фиксирует следующий шаг?"
        )
    return (
        f"Когда новое обращение приходит через «{flow}» и попадает в «{tools}», на каком шаге команда чаще всего вынуждена действовать вручную?"
    )


def _short_reference(text: str) -> str:
    normalised = " ".join(text.split())
    return normalised[:180].rstrip(" .,;:") or "этот процесс"


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
