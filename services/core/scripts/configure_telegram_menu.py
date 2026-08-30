"""Configure the fixed native Telegram commands-menu entrypoint through Edge."""

from __future__ import annotations

import asyncio

from app.adapters.telegram_delivery import TelegramEdgeMenuConfigurer
from app.core.settings import get_settings


async def _run() -> None:
    settings = get_settings()
    if (
        settings.telegram_transport_mode != "edge"
        or not settings.telegram_edge_url
        or not settings.telegram_edge_core_secret
    ):
        raise RuntimeError("Telegram commands menu requires Edge transport")
    await TelegramEdgeMenuConfigurer(
        edge_url=settings.telegram_edge_url,
        secret=settings.telegram_edge_core_secret,
    ).configure_and_verify()


if __name__ == "__main__":
    asyncio.run(_run())
    print("Telegram commands menu configured and verified")
