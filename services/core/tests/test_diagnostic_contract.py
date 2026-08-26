import uuid

from app.schemas.diagnostic import PrepareDiagnosticCommand


def test_diagnostic_prepare_contract_uses_internal_user_id() -> None:
    command = PrepareDiagnosticCommand(user_id=uuid.uuid4())

    assert isinstance(command.user_id, uuid.UUID)
