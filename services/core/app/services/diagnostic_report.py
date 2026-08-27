"""Controlled persistence boundary for a completed diagnostic result."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticReport, DiagnosticSession, Event, User
from app.schemas.diagnostic_report import (
    RecordDiagnosticReportCommand,
    RecordDiagnosticReportResult,
    RecordDiagnosticReportV2Command,
)
from app.schemas.diagnostic_result_v2 import validate_diagnostic_result_v2_catalog_membership
from app.diagnostic_assets import load_solution_catalog


class DiagnosticReportService:
    """Stores an already validated report; it never invokes an AI provider."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self, command: RecordDiagnosticReportCommand, *, result_version: str = "v1", result_json: dict[str, object] | None = None
    ) -> RecordDiagnosticReportResult:
        diagnostic = await self._session.get(DiagnosticSession, command.diagnostic_session_id)
        if diagnostic is None:
            raise ValueError("diagnostic session not found")

        existing = await self._session.scalar(
            select(DiagnosticReport).where(
                DiagnosticReport.diagnostic_session_id == diagnostic.id
            )
        )
        if existing is not None:
            return RecordDiagnosticReportResult(
                report_id=existing.id,
                diagnostic_session_id=diagnostic.id,
                created=False,
                status=diagnostic.status,
            )
        if diagnostic.status not in {"prepared", "diagnostic_active"}:
            raise ValueError("diagnostic session is not ready for a report")

        report = DiagnosticReport(
            diagnostic_session_id=diagnostic.id,
            summary=command.summary,
            priorities_json=[item.model_dump() for item in command.priorities],
            next_steps_json=[item.model_dump() for item in command.next_steps],
            limitations_json=command.limitations,
            role_split_json=command.role_split.model_dump(),
            result_version=result_version,
            result_json=result_json or {},
        )
        diagnostic.status = "diagnostic_completed"
        diagnostic.completed_at = datetime.now(timezone.utc)
        user = await self._session.get(User, diagnostic.user_id)
        if user is None:
            raise RuntimeError("diagnostic session refers to a missing user")
        if user.lifecycle_stage == "diagnostic_in_progress":
            user.lifecycle_stage = "diagnostic_ready"
        self._session.add(report)
        self._session.add(
            Event(
                user_id=user.id,
                kind="diagnostic_ready",
                payload_json={"diagnostic_session_id": str(diagnostic.id)},
            )
        )
        await self._session.flush()
        return RecordDiagnosticReportResult(
            report_id=report.id,
            diagnostic_session_id=diagnostic.id,
            created=True,
            status=diagnostic.status,
        )

    async def record_v2(self, command: RecordDiagnosticReportV2Command) -> RecordDiagnosticReportResult:
        """Persist v2 alongside legacy projection without overwriting v1 reports."""
        result = validate_diagnostic_result_v2_catalog_membership(command.result, load_solution_catalog())
        return await self.record(
            RecordDiagnosticReportCommand(
                diagnostic_session_id=command.diagnostic_session_id,
                summary=result.client_view.what_is_happening,
                priorities=[{
                    "title": "Где теряется результат",
                    "reason": result.client_view.where_result_is_lost,
                    "confidence": "medium",
                }],
                next_steps=[{
                    "title": "Как это может работать",
                    "action": result.client_view.future_process,
                }],
                limitations=result.client_view.open_questions,
                role_split={
                    "automation": result.client_view.system_responsibilities,
                    "ai": result.client_view.ai_responsibilities,
                    "human": result.client_view.human_responsibilities,
                },
            ),
            result_version="v2",
            result_json=result.model_dump(mode="json"),
        )
