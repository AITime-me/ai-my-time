"""Bounded attribution vocabulary for Telegram starts originating on the website."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsiteStartAttribution:
    source_code: str
    intent: str


WEBSITE_START_ALLOWLIST: dict[str, WebsiteStartAttribution] = {
    "site_consultant": WebsiteStartAttribution(
        source_code="website_consultant",
        intent="general",
    ),
    "site_consultant_radar": WebsiteStartAttribution(
        source_code="website_consultant",
        intent="radar",
    ),
    "site_contacts": WebsiteStartAttribution(
        source_code="website_contacts",
        intent="general",
    ),
    "site_header": WebsiteStartAttribution(
        source_code="website_header",
        intent="general",
    ),
}

WEBSITE_SOURCE_LABELS: dict[str, str] = {
    "website_consultant": "Сайт · AI-консультант",
    "website_contacts": "Сайт · Контакты",
    "website_header": "Сайт · Header",
}

WEBSITE_INTENT_LABELS: dict[str, str] = {
    "radar": "Радар спроса",
    "general": "Общий запрос",
}


def website_start_attribution(entry_code: str) -> WebsiteStartAttribution | None:
    """Resolve only explicitly supported website payloads."""

    return WEBSITE_START_ALLOWLIST.get(entry_code)


def website_source_label(source_code: str | None) -> str | None:
    if source_code is None:
        return None
    return WEBSITE_SOURCE_LABELS.get(source_code)


def website_intent_label(intent: str | None) -> str | None:
    if intent is None:
        return None
    return WEBSITE_INTENT_LABELS.get(intent)
