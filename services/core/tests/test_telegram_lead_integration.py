"""Real PostgreSQL proof of the narrow secret-checked Telegram /start ingress."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_private_start_is_secret_checked_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _test_database_url()
    asyncio.run(_clear_conference_tables(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "test-lead-webhook-secret")
    get_settings.cache_clear()
    payload = {
        "update_id": 1001,
        "message": {
            "chat": {"type": "private"},
            "from": {"id": 901001},
            "text": "/start qr_conf_main",
        },
    }
    try:
        with TestClient(create_app()) as client:
            assert client.post("/webhooks/telegram/lead", json=payload).status_code == 401
            headers = {"X-Telegram-Bot-Api-Secret-Token": "test-lead-webhook-secret"}
            assert client.post("/webhooks/telegram/lead", json=payload, headers=headers).status_code == 204
            assert client.post("/webhooks/telegram/lead", json=payload, headers=headers).status_code == 204
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_conference_tables(database_url))


async def _clear_conference_tables(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE diagnostic_reports, diagnostic_sessions, profile_answers, "
                    "business_profiles, conference_entries, events, touchpoints, "
                    "user_identities, users RESTART IDENTITY CASCADE"
                )
            )
    finally:
        await factory.kw["bind"].dispose()
