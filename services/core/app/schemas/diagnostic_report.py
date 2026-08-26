from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class DiagnosticPriorityInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=600)
    confidence: str = Field(pattern="^(high|medium|low)$")


class DiagnosticNextStepInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    action: str = Field(min_length=1, max_length=600)


class RecordDiagnosticReportCommand(BaseModel):
    diagnostic_session_id: uuid.UUID
    summary: str = Field(min_length=1, max_length=2000)
    priorities: list[DiagnosticPriorityInput] = Field(min_length=1, max_length=5)
    next_steps: list[DiagnosticNextStepInput] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=5)


class RecordDiagnosticReportResult(BaseModel):
    report_id: uuid.UUID
    diagnostic_session_id: uuid.UUID
    created: bool
    status: str
