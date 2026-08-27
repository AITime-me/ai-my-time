"""Versioned, editable Diagnostic AI text assets.

The provider integration receives this bundle later; runtime business code owns
selection and validation, not product methodology or knowledge text.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

DEFAULT_VERSION = "v1"


@dataclass(frozen=True)
class DiagnosticPromptBundle:
    version: str
    guardrails: str
    prompt: str
    knowledge_base: str
    price_reply: str


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
    )
