"""Persist structured profile answers before any AI diagnosis runs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessProfile, Event, ProfileAnswer, User
from app.schemas.profile import SaveProfileAnswersCommand, SaveProfileAnswersResult


class ProfileService:
    """A provider-neutral profile writer. The caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, command: SaveProfileAnswersCommand) -> SaveProfileAnswersResult:
        user = await self._session.get(User, command.user_id)
        if user is None:
            raise ValueError("user not found")

        profile = await self._session.scalar(
            select(BusinessProfile).where(BusinessProfile.user_id == user.id)
        )
        if profile is None:
            profile = BusinessProfile(user_id=user.id, status="in_progress")
            self._session.add(profile)
            await self._session.flush()

        for answer in command.answers:
            previous_revision = await self._session.scalar(
                select(func.max(ProfileAnswer.revision)).where(
                    ProfileAnswer.user_id == user.id,
                    ProfileAnswer.question_code == answer.question_code,
                )
            )
            self._session.add(
                ProfileAnswer(
                    user_id=user.id,
                    question_code=answer.question_code,
                    answer_json={"value": answer.value},
                    revision=(previous_revision or 0) + 1,
                )
            )

        if command.complete:
            profile.status = "completed"
            profile.completed_at = datetime.now(timezone.utc)
            if user.lifecycle_stage == "profiling":
                user.lifecycle_stage = "diagnostic_in_progress"
            event_kind = "profile_completed"
        else:
            event_kind = "profile_answers_saved"

        self._session.add(
            Event(
                user_id=user.id,
                kind=event_kind,
                payload_json={"answer_count": len(command.answers)},
            )
        )
        await self._session.flush()
        return SaveProfileAnswersResult(
            user_id=user.id,
            profile_status=profile.status,
            saved_answers=len(command.answers),
        )
