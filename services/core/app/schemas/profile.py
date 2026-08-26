from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


PROFILE_QUESTION_CODES = frozenset(
    {
        "business_type",
        "team_size",
        "client_flow",
        "current_tools",
        "primary_pain",
        "automation_goal",
    }
)


class ProfileAnswerInput(BaseModel):
    question_code: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)

    @field_validator("question_code")
    @classmethod
    def question_must_be_in_mvp_set(cls, value: str) -> str:
        if value not in PROFILE_QUESTION_CODES:
            raise ValueError("unsupported profile question")
        return value


class SaveProfileAnswersCommand(BaseModel):
    user_id: uuid.UUID
    answers: list[ProfileAnswerInput] = Field(min_length=1, max_length=6)
    complete: bool = False

    @field_validator("answers")
    @classmethod
    def answers_must_not_repeat_question(cls, answers: list[ProfileAnswerInput]) -> list[ProfileAnswerInput]:
        if len({answer.question_code for answer in answers}) != len(answers):
            raise ValueError("profile question may be answered once per command")
        return answers


class SaveProfileAnswersResult(BaseModel):
    user_id: uuid.UUID
    profile_status: str
    saved_answers: int
