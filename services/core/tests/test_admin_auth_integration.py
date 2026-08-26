"""Real PostgreSQL proof for Admin account/session primitives."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import AdminSession
from app.services.admin_auth import AdminAuthService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_admin_owner_session_is_hashed_and_reusable() -> None:
    asyncio.run(_run_auth_flow(_test_database_url()))


async def _run_auth_flow(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    try:
        async with session_scope(session_factory) as session:
            await session.execute(text("TRUNCATE TABLE admin_sessions, admin_users RESTART IDENTITY CASCADE"))

        async with session_scope(session_factory) as session:
            owner = await AdminAuthService(session).bootstrap_owner(
                email="owner@example.test", password="StrongPassword2026"
            )
            assert owner.role == "owner"

        async with session_scope(session_factory) as session:
            login = await AdminAuthService(session).login(
                email="OWNER@example.test", password="StrongPassword2026"
            )
            assert login.actor.role == "owner"
            digest = await session.scalar(select(AdminSession.token_hash))
            assert digest is not None
            assert digest != login.session_token

        async with session_scope(session_factory) as session:
            actor = await AdminAuthService(session).authenticate(
                session_token=login.session_token
            )
            assert actor.user_id == owner.user_id
    finally:
        try:
            async with session_scope(session_factory) as session:
                await session.execute(text("TRUNCATE TABLE admin_sessions, admin_users RESTART IDENTITY CASCADE"))
        finally:
            await session_factory.kw["bind"].dispose()
