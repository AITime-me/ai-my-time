"""Controlled boundary between a future Diagnostic AI provider and the MVP core.

The provider sees only a prepared, versioned profile snapshot and must return
the strict report shape. This module does not know providers, keys or URLs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticReport, DiagnosticSession
from app.schemas.diagnostic_report import (
    DiagnosticNextStepInput,
    DiagnosticPriorityInput,
    DiagnosticRoleSplitInput,
    RecordDiagnosticReportCommand,
    RecordDiagnosticReportResult,
)
from app.services.diagnostic_report import DiagnosticReportService
from app.services.outbox import OutboundQueue


@dataclass(frozen=True)
class DiagnosticInput:
    diagnostic_session_id: uuid.UUID
    user_id: uuid.UUID
    profile_snapshot: dict[str, object]


@dataclass(frozen=True)
class GeneratedDiagnostic:
    summary: str
    priorities: list[DiagnosticPriorityInput]
    next_steps: list[DiagnosticNextStepInput]
    limitations: list[str]
    role_split: DiagnosticRoleSplitInput = field(default_factory=DiagnosticRoleSplitInput)


@dataclass(frozen=True)
class DiagnosticConversationInput:
    diagnostic_session_id: uuid.UUID
    user_id: uuid.UUID
    profile_snapshot: dict[str, object]
    turns: list[tuple[str, str]]


@dataclass(frozen=True)
class DiagnosticConversationResponse:
    question: str | None = None
    diagnostic: GeneratedDiagnostic | None = None


class DiagnosticProvider(Protocol):
    async def generate(self, diagnostic_input: DiagnosticInput) -> GeneratedDiagnostic: ...


class DiagnosticConversationProvider(Protocol):
    async def advance(self, diagnostic_input: DiagnosticConversationInput) -> DiagnosticConversationResponse: ...


class DiagnosticGenerationService:
    """Invokes an injected provider once and persists only validated output."""

    def __init__(self, session: AsyncSession, provider: DiagnosticProvider) -> None:
        self._session = session
        self._provider = provider
        self._outbox = OutboundQueue(session)

    async def complete(self, *, diagnostic_session_id: uuid.UUID) -> RecordDiagnosticReportResult:
        diagnostic = await self._session.get(DiagnosticSession, diagnostic_session_id)
        if diagnostic is None:
            raise ValueError("diagnostic session not found")
        existing = await self._session.scalar(
            select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == diagnostic.id)
        )
        if existing is not None:
            return RecordDiagnosticReportResult(
                report_id=existing.id,
                diagnostic_session_id=diagnostic.id,
                created=False,
                status=diagnostic.status,
            )
        if diagnostic.status not in {"prepared", "diagnostic_active"}:
            raise ValueError("diagnostic session is not ready for generation")

        generated = await self._provider.generate(
            DiagnosticInput(
                diagnostic_session_id=diagnostic.id,
                user_id=diagnostic.user_id,
                profile_snapshot=diagnostic.input_snapshot_json,
            )
        )
        result = await DiagnosticReportService(self._session).record(
            RecordDiagnosticReportCommand(
                diagnostic_session_id=diagnostic.id,
                summary=generated.summary,
                priorities=generated.priorities,
                next_steps=generated.next_steps,
                limitations=generated.limitations,
                role_split=generated.role_split,
            )
        )
        if result.created:
            await self._outbox.enqueue(
                user_id=diagnostic.user_id,
                channel="telegram_lead",
                payload={
                    "kind": "message",
                    "text": generated.summary,
                    "buttons": [
                        {"text": "Записаться на онлайн-консультацию", "callback_data": f"diagnostic:consult:{diagnostic.id}"}
                    ],
                },
                dedupe_key=f"diagnostic:{diagnostic.id}:result",
            )
        return result
