from __future__ import annotations

import uuid

from pydantic import BaseModel


class PrepareDiagnosticCommand(BaseModel):
    user_id: uuid.UUID


class PrepareDiagnosticResult(BaseModel):
    diagnostic_session_id: uuid.UUID
    status: str
    profile_answer_count: int
