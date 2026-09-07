"""HTTP proof for public, Admin and Assistant boundary separation."""

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
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url: pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    return url


async def _clear(url: str) -> None:
    factory = create_session_factory(url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("DELETE FROM assistant_runs"))
            await session.execute(text("DELETE FROM assistant_messages"))
            await session.execute(text("DELETE FROM intake_requests"))
            await session.execute(text("DELETE FROM consent_records"))
            await session.execute(text("DELETE FROM assistant_conversations"))
            await session.execute(text("DELETE FROM assistant_channel_bindings"))
            await session.execute(text("DELETE FROM assistant_profile_versions"))
            await session.execute(text("DELETE FROM assistant_profiles"))
            await session.execute(text("DELETE FROM site_legal_document_versions"))
            await session.execute(text("DELETE FROM site_legal_documents"))
            await session.execute(text("DELETE FROM site_services"))
            await session.execute(text("DELETE FROM site_cases"))
            await session.execute(text("DELETE FROM site_faq"))
            await session.execute(text("DELETE FROM site_settings"))
            await session.execute(text("DELETE FROM admin_audit_events"))
            await session.execute(text("DELETE FROM admin_sessions"))
            await session.execute(text("DELETE FROM admin_users WHERE email = 'unified-api@example.test'"))
    finally:
        await factory.kw["bind"].dispose()


def test_unified_admin_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    url = _database_url(); asyncio.run(_clear(url)); monkeypatch.setenv("DATABASE_URL", url); get_settings.cache_clear()
    try:
        async def bootstrap() -> None:
            factory = create_session_factory(url)
            try:
                async with session_scope(factory) as session:
                    await AdminAuthService(session).bootstrap_owner(email="unified-api@example.test", password="StrongPassword2026")
            finally: await factory.kw["bind"].dispose()
        asyncio.run(bootstrap())
        with TestClient(create_app()) as client:
            assert client.get("/admin/site/services").status_code == 401
            assert client.get("/public/site/services").json() == []
            assert client.post("/admin/auth/login", json={"email": "unified-api@example.test", "password": "StrongPassword2026"}).status_code == 200
            assert client.put("/admin/site/settings", json={"site_title": "AI My Time", "contacts_json": {"telegram": "https://t.me/example"}}).status_code == 200
            assert client.get("/public/site/settings").json()["site_title"] == "AI My Time"
            service = client.post("/admin/site/services", json={"slug": "api-test", "title": "API test", "is_active": True})
            assert service.status_code == 201
            assert client.get("/public/site/services").json()[0]["slug"] == "api-test"
            draft = client.post("/admin/assistant/profiles/drafts", json={"key": "web-test", "title": "Web test", "config_json": {"knowledge_namespace": "site_assistant"}}).json()
            published = client.post(f"/admin/assistant/profiles/versions/{draft['version_id']}/publish")
            assert published.status_code == 200
            assert client.put("/admin/assistant/bindings/web", json={"profile_id": draft["profile_id"], "is_active": True}).status_code == 200
            conversation = client.post("/assistant/conversations", json={"channel": "web"}).json()
            headers = {"X-Assistant-Session": conversation["session_token"]}
            assert client.post(f"/assistant/conversations/{conversation['conversation_id']}/messages", headers=headers, json={"content": "Нужна консультация"}).status_code == 201
            intake = client.post(f"/assistant/conversations/{conversation['conversation_id']}/intakes", headers=headers, json={"kind": "consultation", "summary": "Нужна консультация"})
            assert intake.status_code == 201
            assert client.get("/admin/assistant/intakes").json()[0]["id"] == intake.json()["id"]
            assert client.post(f"/assistant/conversations/{conversation['conversation_id']}/messages", json={"content": "no token"}).status_code == 401
    finally:
        get_settings.cache_clear(); asyncio.run(_clear(url))
