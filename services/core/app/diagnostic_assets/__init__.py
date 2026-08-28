"""Versioned, editable Diagnostic AI text assets.

The provider integration receives this bundle later; runtime business code owns
selection and validation, not product methodology or knowledge text.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files

from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.schemas.solution_catalog import SolutionCatalogV1

DEFAULT_VERSION = "v1"


@dataclass(frozen=True)
class DiagnosticPromptBundle:
    version: str
    guardrails: str
    prompt: str
    knowledge_base: str
    price_reply: str
    solution_catalog: SolutionCatalogV1


def load_diagnostic_prompt_bundle(version: str = DEFAULT_VERSION) -> DiagnosticPromptBundle:
    if version != DEFAULT_VERSION:
        raise ValueError("unsupported diagnostic prompt version")
    root = files(__package__)
    return DiagnosticPromptBundle(
        version=version,
        guardrails=(root / f"guardrails.{version}.md").read_text(encoding="utf-8").strip(),
        prompt=(root / f"prompt.{version}.md").read_text(encoding="utf-8").strip(),
        knowledge_base=(root / f"knowledge_base.{version}.md").read_text(encoding="utf-8").strip(),
        price_reply=(root / f"price_reply.{version}.md").read_text(encoding="utf-8").strip(),
        solution_catalog=load_solution_catalog(),
    )


def load_solution_catalog(version: str = "v1") -> SolutionCatalogV1:
    if version != "v1":
        raise ValueError("unsupported solution catalog version")
    root = files(__package__)
    return SolutionCatalogV1.model_validate_json(
        (root / f"solution_catalog.{version}.json").read_text(encoding="utf-8")
    )


def load_diagnostic_result_contract(version: str = "v2") -> dict[str, object]:
    """Load the version marker and allowed vocabulary for an internal result contract."""
    if version != "v2":
        raise ValueError("unsupported diagnostic result contract version")
    root = files(__package__)
    raw = json.loads((root / f"diagnostic_result.{version}.json").read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("contract_version") != version:
        raise ValueError("invalid diagnostic result contract asset")
    return raw


def validate_diagnostic_result_v2(payload: object) -> DiagnosticResultV2:
    """Validate v2 without changing the persisted v1 report boundary."""
    result = DiagnosticResultV2.model_validate(payload)
    catalog = load_solution_catalog()
    from app.schemas.diagnostic_result_v2 import validate_diagnostic_result_v2_catalog_membership

    return validate_diagnostic_result_v2_catalog_membership(result, catalog)


def normalize_diagnostic_result_v2(payload: object) -> tuple[object, tuple[str, ...]]:
    """Trim provider list overflow before strict v2 validation.

    The model's ordering is its stated priority.  This deliberately repairs
    only overlong responsibility lists, never invents fields or values, and
    leaves every other contract violation for the strict validator.
    """
    if not isinstance(payload, dict):
        return payload, ()
    normalized = deepcopy(payload)
    client_view = normalized.get("client_view")
    if not isinstance(client_view, dict):
        return normalized, ()
    changed: list[str] = []
    for field in ("system_responsibilities", "ai_responsibilities", "human_responsibilities"):
        value = client_view.get(field)
        if isinstance(value, list) and len(value) > 3:
            client_view[field] = value[:3]
            changed.append(field)
    return normalized, tuple(changed)
