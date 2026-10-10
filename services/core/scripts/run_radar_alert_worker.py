"""Bounded polling process for the isolated Demand Radar Telegram Bot outbox."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from app.adapters.telegram_delivery import TelegramRadarAlertTransport
from app.core.settings import get_settings
from app.db.session import create_session_factory
from app.services.radar_alert_delivery import RadarAlertWorker


def _load_tokens(path: str) -> dict[str, str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Radar Bot token file must be a JSON object")
    return {key: value for key, value in raw.items() if isinstance(key, str) and isinstance(value, str)}


async def main() -> None:
    settings = get_settings()
    if not settings.database_url or not settings.radar_alert_bot_tokens_path:
        raise RuntimeError("DATABASE_URL and RADAR_ALERT_BOT_TOKENS_PATH are required")
    factory = create_session_factory(settings.database_url)
    worker = RadarAlertWorker(factory, TelegramRadarAlertTransport(tokens=_load_tokens(settings.radar_alert_bot_tokens_path)))
    try:
        while True:
            sent = await worker.run_once()
            await asyncio.sleep(0.2 if sent else 2)
    finally:
        await factory.kw["bind"].dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
