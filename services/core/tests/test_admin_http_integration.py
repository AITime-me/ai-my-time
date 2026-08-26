"""HTTP proof: no registration, hashed session stays in an HttpOnly cookie."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.services.admin_auth import AdminAuthService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_admin_login_is_cookie_only_and_logout_revokes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _test_database_url()
    asyncio.run(_bootstrap_test_owner(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            login = client.post(
                "/admin/auth/login",
                json={"email": "owner@example.test", "password": "StrongPassword2026"},
            )
            assert login.status_code == 200
            assert "session_token" not in login.text
            assert "HttpOnly" in login.headers["set-cookie"]
            assert client.get("/admin/auth/me").json()["role"] == "owner"
            assert client.post("/admin/auth/logout").status_code == 403
            assert client.post(
                "/admin/auth/logout", headers={"Origin": "http://testserver"}
            ).status_code == 204
            assert client.get("/admin/auth/me").status_code == 401
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_admin_tables(database_url))


async def _bootstrap_test_owner(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE admin_sessions, admin_users RESTART IDENTITY CASCADE"))
            await AdminAuthService(session).bootstrap_owner(
                email="owner@example.test", password="StrongPassword2026"
            )
    finally:
        await factory.kw["bind"].dispose()


async def _clear_admin_tables(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE admin_sessions, admin_users RESTART IDENTITY CASCADE"))
    finally:
        await factory.kw["bind"].dispose()
