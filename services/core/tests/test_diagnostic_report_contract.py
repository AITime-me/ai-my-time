import uuid

import pytest
from pydantic import ValidationError

from app.schemas.diagnostic_report import RecordDiagnosticReportCommand


def test_diagnostic_report_contract_accepts_structured_result() -> None:
    command = RecordDiagnosticReportCommand(
        diagnostic_session_id=uuid.uuid4(),
        summary="Нужно убрать ручную передачу новой заявки между сотрудниками.",
        priorities=[{"title": "Статус заявки", "reason": "Следующий шаг не виден", "confidence": "high"}],
        next_steps=[{"title": "Единый вход", "action": "Зафиксировать один канал новых заявок"}],
    )

    assert command.priorities[0].confidence == "high"


def test_diagnostic_report_contract_rejects_unstructured_priority() -> None:
    with pytest.raises(ValidationError):
        RecordDiagnosticReportCommand(
            diagnostic_session_id=uuid.uuid4(),
            summary="text",
            priorities=[],
            next_steps=[{"title": "step", "action": "action"}],
        )
