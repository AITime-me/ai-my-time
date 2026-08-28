"""Create one owner-approved, user-bound acceptance start link.

This script is deliberately manual and internal. It is not invoked by the API,
worker, deployment or any normal Telegram user flow.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.models import UserIdentity
from app.services.diagnostic_acceptance import DiagnosticAcceptanceService


async def _issue(*, telegram_user_id: str, bot_username: str, ttl_minutes: int) -> None:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    factory = create_session_factory(settings.database_url)
    try:
        async with session_scope(factory) as session:
            user_id = await session.scalar(
                select(UserIdentity.user_id).where(
                    UserIdentity.provider == "telegram",
                    UserIdentity.connection_scope == "ai_my_time_lead_bot",
                    UserIdentity.external_id == telegram_user_id,
                )
            )
            if user_id is None:
                raise RuntimeError("existing Telegram identity was not found")
            issued = await DiagnosticAcceptanceService(session).issue(
                user_id=user_id,
                ttl=timedelta(minutes=ttl_minutes),
            )
        print(f"https://t.me/{bot_username.lstrip('@')}?start={issued.raw_start_parameter}")
        print(f"expires_at={issued.expires_at.isoformat()}")
    finally:
        await factory.kw["bind"].dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue one closed Diagnostic AI acceptance link")
    parser.add_argument("--telegram-user-id", required=True)
    parser.add_argument("--bot-username", required=True)
    parser.add_argument("--ttl-minutes", type=int, default=30)
    args = parser.parse_args()
    if args.ttl_minutes < 1 or args.ttl_minutes > 120:
        parser.error("--ttl-minutes must be between 1 and 120")
    asyncio.run(
        _issue(
            telegram_user_id=args.telegram_user_id,
            bot_username=args.bot_username,
            ttl_minutes=args.ttl_minutes,
        )
    )


if __name__ == "__main__":
    main()
