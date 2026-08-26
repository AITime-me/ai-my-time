"""Read-only Admin projection; authentication and HTTP exposure come later."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConferenceEntry, DiagnosticReport, DiagnosticSession, User
from app.schemas.admin import AdminLeadList, AdminLeadView


class AdminLeadReadService:
    """Small explicit projection for the existing Admin UI, with no PII fields."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent(self, *, limit: int = 50) -> AdminLeadList:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        users = (
            await self._session.scalars(
                select(User).order_by(desc(User.created_at)).limit(limit)
            )
        ).all()
        items: list[AdminLeadView] = []
        for user in users:
            conference_entry = await self._session.scalar(
                select(ConferenceEntry)
                .where(ConferenceEntry.user_id == user.id)
                .order_by(desc(ConferenceEntry.created_at))
                .limit(1)
            )
            diagnostic = await self._session.scalar(
                select(DiagnosticSession)
                .where(DiagnosticSession.user_id == user.id)
                .order_by(desc(DiagnosticSession.created_at))
                .limit(1)
            )
            report_summary: str | None = None
            if diagnostic is not None:
                report = await self._session.scalar(
                    select(DiagnosticReport).where(
                        DiagnosticReport.diagnostic_session_id == diagnostic.id
                    )
                )
                if report is not None:
                    report_summary = report.summary
            items.append(
                AdminLeadView(
                    user_id=user.id,
                    lifecycle_stage=user.lifecycle_stage,
                    conference_code=(
                        conference_entry.conference_code if conference_entry else None
                    ),
                    diagnostic_status=diagnostic.status if diagnostic else None,
                    diagnostic_summary=report_summary,
                    created_at=user.created_at,
                )
            )
        return AdminLeadList(items=items, limit=limit)
