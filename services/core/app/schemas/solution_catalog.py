"""Versioned product catalog contracts for Diagnostic AI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SolutionClassV1(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=1, max_length=160)
    when_to_consider: list[str] = Field(min_length=1, max_length=6)
    boundaries: list[str] = Field(min_length=1, max_length=6)
    includes: list[str] = Field(min_length=1, max_length=10)


class SolutionCatalogV1(BaseModel):
    version: Literal["v1"]
    solution_classes: list[SolutionClassV1] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _has_unique_ids(self) -> "SolutionCatalogV1":
        ids = [item.id for item in self.solution_classes]
        if len(ids) != len(set(ids)):
            raise ValueError("solution catalog ids must be unique")
        return self
