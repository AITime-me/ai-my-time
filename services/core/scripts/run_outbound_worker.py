"""Bounded polling process for the production Telegram Lead Bot outbox."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.adapters.telegram_delivery import TelegramBotTransport, TelegramEdgeTransport, TelegramOpsTransport
from app.core.settings import get_settings
from app.db.session import create_session_factory
from app.services.outbox_delivery import OutboundWorker
from app.services.scheduled_events import ScheduledEventWorker


class RoutedTelegramTransport:
    """Keeps client delivery and private operations delivery independently configured."""

    def __init__(self, *, lead, ops: TelegramOpsTransport | None) -> None:
        self._lead, self._ops = lead, ops

    async def deliver(self, message) -> None:
        if message.channel == "telegram_lead":
            await self._lead.deliver(message)
            return
        if message.channel == "telegram_ops" and self._ops is not None:
            await self._ops.deliver(message)
            return
        raise RuntimeError("outbound channel is not configured")


async def main() -> None:
    settings = get_settings()
    if not settings.database_url: raise RuntimeError("DATABASE_URL is required for outbound worker")
    factory = create_session_factory(settings.database_url)
    if settings.telegram_transport_mode == "edge":
        lead = TelegramEdgeTransport(edge_url=settings.telegram_edge_url or "", secret=settings.telegram_edge_core_secret or "")
    else:
        lead = TelegramBotTransport(token=settings.telegram_bot_token or "")
    ops = None
    if settings.telegram_ops_bot_token_path and settings.telegram_ops_chat_id:
        ops = TelegramOpsTransport(
            token=Path(settings.telegram_ops_bot_token_path).read_text(encoding="utf-8").strip(),
            chat_id=settings.telegram_ops_chat_id,
        )
    worker = OutboundWorker(factory, RoutedTelegramTransport(lead=lead, ops=ops))
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
