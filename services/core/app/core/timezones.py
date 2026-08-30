"""Business-time presentation helpers; storage and scheduling stay in UTC."""

from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW = ZoneInfo("Europe/Moscow")


def format_moscow(value: datetime) -> str:
    """Return the single client-facing appointment representation."""
    if value.tzinfo is None:
        raise ValueError("appointment time must be timezone-aware")
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M МСК")
