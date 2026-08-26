import uuid

import pytest
from pydantic import ValidationError

from app.schemas.profile import SaveProfileAnswersCommand


def test_profile_contract_accepts_a_known_question() -> None:
    command = SaveProfileAnswersCommand(
        user_id=uuid.uuid4(),
        answers=[{"question_code": "primary_pain", "value": "Теряются заявки"}],
    )

    assert command.answers[0].question_code == "primary_pain"


def test_profile_contract_rejects_unknown_question() -> None:
    with pytest.raises(ValidationError):
        SaveProfileAnswersCommand(
            user_id=uuid.uuid4(),
            answers=[{"question_code": "anything", "value": "text"}],
        )
