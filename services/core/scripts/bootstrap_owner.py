"""One-time Admin owner bootstrap. Password is never accepted as an argument."""

from __future__ import annotations

import argparse
import asyncio
import getpass

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.services.admin_auth import AdminAuthService


async def _run(email: str) -> None:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    password = getpass.getpass("Пароль владельца: ")
    confirmation = getpass.getpass("Повторите пароль: ")
    if password != confirmation:
        raise RuntimeError("password confirmation does not match")
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await AdminAuthService(session).bootstrap_owner(email=email, password=password)
    finally:
        await factory.kw["bind"].dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first A.I. My Time Admin owner")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    asyncio.run(_run(args.email))
    print("Owner account created. Bootstrap is now closed.")


if __name__ == "__main__":
    main()
