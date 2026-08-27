"""Prepare deterministic diagnostic input before an AI provider is attached."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessProfile, DiagnosticSession, Event, ProfileAnswer, User
from app.schemas.diagnostic import PrepareDiagnosticCommand, PrepareDiagnosticResult


class DiagnosticPreparationService:
    """Creates a repeatable snapshot; it does not call an LLM or publish text."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def prepare(self, command: PrepareDiagnosticCommand) -> PrepareDiagnosticResult:
        user = await self._session.get(User, command.user_id)
        if user is None:
            raise ValueError("user not found")

        profile = await self._session.scalar(
            select(BusinessProfile).where(BusinessProfile.user_id == user.id)
        )
        if profile is None or profile.status != "completed":
            raise ValueError("profile is not complete")

        answer_rows = (
            await self._session.scalars(
                select(ProfileAnswer)
                .where(ProfileAnswer.user_id == user.id)
                .order_by(ProfileAnswer.question_code, desc(ProfileAnswer.revision))
            )
        ).all()
        latest_answers: dict[str, object] = {}
        for answer in answer_rows:
            latest_answers.setdefault(answer.question_code, answer.answer_json)

        diagnostic = DiagnosticSession(
            user_id=user.id,
            status="diagnostic_active",
            input_snapshot_json={"profile_answers": latest_answers},
        )
        self._session.add(diagnostic)
        self._session.add(
            Event(
                user_id=user.id,
                kind="diagnostic_active",
                payload_json={"profile_answer_count": len(latest_answers)},
            )
        )
        await self._session.flush()

        return PrepareDiagnosticResult(
            diagnostic_session_id=diagnostic.id,
            status=diagnostic.status,
            profile_answer_count=len(latest_answers),
        )
