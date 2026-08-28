"""Admin knowledge stays versioned and is only changed by an authenticated actor."""

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


def _database_url() -> str:
    value = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not value:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    return value


async def _clear(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE knowledge_versions, knowledge_assets, admin_sessions, admin_users RESTART IDENTITY CASCADE"))
    finally:
        await factory.kw["bind"].dispose()


def test_knowledge_requires_explicit_publish_and_ui_is_cookie_protected(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = _database_url()
    asyncio.run(_clear(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        async def bootstrap() -> None:
            factory = create_session_factory(database_url)
            try:
                async with session_scope(factory) as session:
                    await AdminAuthService(session).bootstrap_owner(email="knowledge@example.test", password="StrongPassword2026")
            finally:
                await factory.kw["bind"].dispose()
        asyncio.run(bootstrap())
        with TestClient(create_app()) as client:
            page = client.get("/admin/")
            assert page.status_code == 200
            assert "AI My Time — Admin" in page.text
            assert client.get("/admin/knowledge").status_code == 401
            assert client.post("/admin/auth/login", json={"email": "knowledge@example.test", "password": "StrongPassword2026"}).status_code == 200
            draft = client.post("/admin/knowledge/drafts", json={"namespace": "faq", "key": "consultation", "title": "Консультация", "content_json": {"text": "Напишем вам"}})
            assert draft.status_code == 201
            draft_id = draft.json()["knowledge_version_id"]
            assert client.get("/admin/knowledge").json()["items"][0]["published_version_id"] is None
            assert client.post(f"/admin/knowledge/versions/{draft_id}/publish").json()["status"] == "published"
            second = client.post("/admin/knowledge/drafts", json={"namespace": "faq", "key": "consultation", "title": "Консультация", "content_json": {"text": "Уточним время"}}).json()
            assert client.post(f"/admin/knowledge/versions/{second['knowledge_version_id']}/publish").json()["status"] == "published"
            assert client.post(f"/admin/knowledge/versions/{draft_id}/rollback").json()["status"] == "published"
            asset = client.get("/admin/knowledge").json()["items"][0]
            assert asset["published_version_id"] == draft_id
            assert client.post("/admin/knowledge/drafts", json={"namespace": "prompts", "key": "blocked", "title": "Blocked", "content_json": {"x": 1}}).status_code == 422
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear(database_url))
