from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_SYSTEM_CHARS = 32_000
MAX_MESSAGE_CHARS = 2_000
MAX_MESSAGES = 11
MAX_DIALOGUE_CHARS = 8_000


class ConsultantMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ConsultantCompleteRequest(BaseModel):
    """Normalized dialogue from the trusted website server; never from a browser."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(min_length=1, max_length=MAX_SYSTEM_CHARS)
    messages: list[ConsultantMessage] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def _bounded_dialogue(self) -> "ConsultantCompleteRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must come from the user")
        if sum(len(message.text) for message in self.messages) > MAX_DIALOGUE_CHARS:
            raise ValueError("dialogue is too long")
        return self


class ConsultantCompleteResponse(BaseModel):
    text: str
