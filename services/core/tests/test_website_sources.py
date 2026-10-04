import pytest

from app.core.website_sources import website_start_attribution
from app.services.website_intake import _website_start_marker_id


@pytest.mark.parametrize(
    ("payload", "source_code", "intent"),
    (
        ("site_consultant", "website_consultant", "general"),
        ("site_consultant_radar", "website_consultant", "radar"),
        ("site_contacts", "website_contacts", "general"),
        ("site_header", "website_header", "general"),
    ),
)
def test_website_start_payload_allowlist(payload: str, source_code: str, intent: str) -> None:
    attribution = website_start_attribution(payload)

    assert attribution is not None
    assert attribution.source_code == source_code
    assert attribution.intent == intent


@pytest.mark.parametrize(
    "payload",
    ("unknown", "website_evil", "site_consultant_extra", "", "SITE_CONSULTANT"),
)
def test_unknown_start_payload_does_not_create_website_attribution(payload: str) -> None:
    assert website_start_attribution(payload) is None


def test_fallback_message_interaction_is_scoped_to_telegram_user() -> None:
    first = _website_start_marker_id(
        telegram_user_id="910101",
        interaction_id="telegram-message:77",
    )

    assert first == _website_start_marker_id(
        telegram_user_id="910101",
        interaction_id="telegram-message:77",
    )
    assert first != _website_start_marker_id(
        telegram_user_id="910102",
        interaction_id="telegram-message:77",
    )
