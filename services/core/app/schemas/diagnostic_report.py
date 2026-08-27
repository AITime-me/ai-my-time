from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.diagnostic_result_v2 import DiagnosticResultV2


class DiagnosticPriorityInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=600)
    confidence: str = Field(pattern="^(high|medium|low)$")


class DiagnosticNextStepInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    action: str = Field(min_length=1, max_length=600)


class DiagnosticRoleSplitInput(BaseModel):
    automation: list[str] = Field(default_factory=list, max_length=3)
    ai: list[str] = Field(default_factory=list, max_length=3)
    human: list[str] = Field(default_factory=list, max_length=3)


class RecordDiagnosticReportCommand(BaseModel):
    diagnostic_session_id: uuid.UUID
    summary: str = Field(min_length=1, max_length=2000)
    priorities: list[DiagnosticPriorityInput] = Field(min_length=1, max_length=5)
    next_steps: list[DiagnosticNextStepInput] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list, max_length=5)
    role_split: DiagnosticRoleSplitInput = Field(default_factory=DiagnosticRoleSplitInput)


class RecordDiagnosticReportResult(BaseModel):
    report_id: uuid.UUID
    diagnostic_session_id: uuid.UUID
    created: bool
    status: str


class RecordDiagnosticReportV2Command(BaseModel):
    """New versioned result boundary; v1 remains available for existing reports."""

    diagnostic_session_id: uuid.UUID
    result: DiagnosticResultV2
