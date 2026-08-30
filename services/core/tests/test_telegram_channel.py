import pytest

from app.core.settings import get_settings
from app.core.telegram_channel import channel_callback_button, channel_url


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_channel_button_uses_public_channel_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_CHANNEL_URL", raising=False)
    assert channel_url() == "https://t.me/AIautomationsales"
    assert channel_callback_button("session") == {
        "text": "Перейти в Telegram-канал",
        "url": "https://t.me/AIautomationsales",
    }


def test_channel_callback_uses_configured_tme_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_CHANNEL_URL", "https://t.me/AIautomationsales")
    get_settings.cache_clear()
    assert channel_url() == "https://t.me/AIautomationsales"
    assert channel_callback_button("session") == {
        "text": "Перейти в Telegram-канал",
        "url": "https://t.me/AIautomationsales",
    }


def test_channel_url_rejects_non_telegram_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_CHANNEL_URL", "https://example.com/not-a-channel")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="Telegram channel URL"):
        channel_url()
