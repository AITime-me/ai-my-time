import pytest
from pydantic import ValidationError

from app.schemas.conference import ConferenceStartCommand


def test_conference_start_contract_accepts_stable_telegram_id() -> None:
    command = ConferenceStartCommand(telegram_user_id="123456", qr_code="conf-main")

    assert command.conference_code == "conference_2026"
    assert command.telegram_user_id == "123456"


def test_conference_start_contract_rejects_non_numeric_telegram_id() -> None:
    with pytest.raises(ValidationError):
        ConferenceStartCommand(telegram_user_id="@mutable_username")
