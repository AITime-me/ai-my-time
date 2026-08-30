"""Bounded polling process for the production Telegram Lead Bot outbox."""

from __future__ import annotations

import asyncio
import logging

from app.adapters.telegram_delivery import TelegramBotTransport
from app.core.settings import get_settings
from app.db.session import create_session_factory
from app.services.outbox_delivery import OutboundWorker
from app.services.scheduled_events import ScheduledEventWorker


async def main() -> None:
    settings = get_settings()
    if not settings.database_url or not settings.telegram_bot_token:
        raise RuntimeError("DATABASE_URL and TELEGRAM_BOT_TOKEN are required for outbound worker")
    factory = create_session_factory(settings.database_url)
    worker = OutboundWorker(factory, TelegramBotTransport(token=settings.telegram_bot_token))
    scheduler = ScheduledEventWorker(factory)
    try:
        while True:
            fired = await scheduler.run_once()
            sent = await worker.run_once()
            await asyncio.sleep(0.2 if sent or fired else 2)
    finally:
        await factory.kw["bind"].dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
