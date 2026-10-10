"""Deterministic v1 include/exclude matcher proofs (no database)."""

from __future__ import annotations

from app.models import RadarSearchRule
from app.services.radar_matching import evaluate_radar_rules, normalize_radar_text, rule_matches_text


def _rule(key: str, kind: str, expression: object, *, enabled: bool = True) -> RadarSearchRule:
    return RadarSearchRule(rule_key=key, kind=kind, expression=expression, enabled=enabled)


def test_normalization_is_casefolded_unicode_and_whitespace_stable() -> None:
    assert normalize_radar_text("  CRM\u00a0Автоматизация  ") == "crm автоматизация"


def test_include_terms_are_a_conjunction_and_rule_keys_are_sorted() -> None:
    result = evaluate_radar_rules(
        text="Need CRM automation for incoming leads",
        rules=[
            _rule("z-crm", "include", {"terms": ["CRM"]}),
            _rule("a-crm-leads", "include", {"terms": ["crm", "leads"]}),
            _rule("not-all", "include", {"terms": ["crm", "telegram"]}),
        ],
    )
    assert result.status == "matched"
    assert result.matched_rule_keys == ["a-crm-leads", "z-crm"]
    assert result.excluded_rule_keys == []


def test_exclusion_has_precedence_even_when_an_include_matches() -> None:
    result = evaluate_radar_rules(
        text="CRM automation for gambling leads",
        rules=[
            _rule("include-crm", "include", {"terms": ["crm"]}),
            _rule("exclude-gambling", "exclude", {"terms": ["gambling"]}),
        ],
    )
    assert result.status == "excluded"
    assert result.matched_rule_keys == ["include-crm"]
    assert result.excluded_rule_keys == ["exclude-gambling"]


def test_invalid_or_disabled_rules_fail_closed() -> None:
    assert not rule_matches_text(expression={"terms": []}, normalized_text="crm")
    assert not rule_matches_text(expression={"terms": ["crm", 1]}, normalized_text="crm")
    result = evaluate_radar_rules(
        text="CRM automation",
        rules=[
            _rule("bad", "include", {"phrase": "crm"}),
            _rule("disabled", "include", {"terms": ["crm"]}, enabled=False),
        ],
    )
    assert result.status == "no_match"
