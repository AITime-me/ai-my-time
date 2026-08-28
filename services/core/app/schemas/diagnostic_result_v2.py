"""Next-version internal result contract, kept separate from persisted v1 reports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.solution_catalog import SolutionCatalogV1

ProblemType = Literal["execution_gap", "feedback_gap", "observability_gap", "growth_gap"]
ProblemScale = Literal[
    "point_task",
    "process",
    "cross_system_contour",
    "systemic_problem",
    "continuous_intellectual_work",
]


class DiagnosticEvidenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: list[str] = Field(min_length=1, max_length=6)
    inferences: list[str] = Field(default_factory=list, max_length=4)
    hypotheses: list[str] = Field(default_factory=list, max_length=4)


class DiagnosticClientViewV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    what_is_happening: str = Field(min_length=1, max_length=1200)
    where_result_is_lost: str = Field(min_length=1, max_length=1200)
    future_process: str = Field(min_length=1, max_length=1200)
    system_responsibilities: list[str] = Field(min_length=1, max_length=3)
    ai_responsibilities: list[str] = Field(default_factory=list, max_length=3)
    human_responsibilities: list[str] = Field(min_length=1, max_length=3)
    open_questions: list[str] = Field(default_factory=list, max_length=2)


class DiagnosticResultV2(BaseModel):
    """Methodology-aligned contract; not yet wired into the v1 provider or renderer."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["v2"]
    evidence: DiagnosticEvidenceV2
    mechanism: str = Field(min_length=1, max_length=1200)
    problem_types: list[ProblemType] = Field(min_length=1, max_length=4)
    problem_scale: ProblemScale
    solution_class_id: str = Field(pattern=r"^[a-z0-9_]+$")
    client_view: DiagnosticClientViewV2

    @model_validator(mode="after")
    def _has_unique_problem_types(self) -> "DiagnosticResultV2":
        if len(self.problem_types) != len(set(self.problem_types)):
            raise ValueError("problem types must be unique")
        return self


def validate_diagnostic_result_v2_catalog_membership(
    result: DiagnosticResultV2, catalog: SolutionCatalogV1
) -> DiagnosticResultV2:
    if result.solution_class_id not in {item.id for item in catalog.solution_classes}:
        raise ValueError("diagnostic result references an unknown solution class")
    return result
