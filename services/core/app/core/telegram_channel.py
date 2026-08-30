"""One bounded, optional public channel link for client-facing CTAs."""

from urllib.parse import urlsplit

from app.core.settings import get_settings


def channel_url() -> str:
    value = get_settings().telegram_channel_url
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in {"t.me", "www.t.me"} or not parsed.path.strip("/"):
        raise ValueError("Telegram channel URL must be a public https://t.me/<handle> URL")
    return value


def channel_callback_button(_diagnostic_id: object) -> dict[str, str] | None:
    """Native inline URL button; Telegram opens the public channel directly."""
    return {"text": "Перейти в Telegram-канал", "url": channel_url()}
