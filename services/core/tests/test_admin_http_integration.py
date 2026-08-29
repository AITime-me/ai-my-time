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
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.outbox_delivery import OutboundDelivery, OutboundWorker
from app.adapters.telegram_delivery import telegram_send_payload


class _RecordingTransport:
    def __init__(self) -> None:
        self.deliveries: list[OutboundDelivery] = []

    async def deliver(self, delivery: OutboundDelivery) -> None:
        assert telegram_send_payload(delivery)["text"] == "Только черновик"
        self.deliveries.append(delivery)


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
    asyncio.run(_create_test_lead(database_url))
    asyncio.run(_enable_broadcast_recipient(database_url))
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get("/admin/leads").status_code == 401
            login = client.post(
                "/admin/auth/login",
                json={"email": "owner@example.test", "password": "StrongPassword2026"},
            )
            assert login.status_code == 200
            assert "session_token" not in login.text
            assert "HttpOnly" in login.headers["set-cookie"]
            assert client.get("/admin/auth/me").json()["role"] == "owner"
            updated_email = client.patch(
                "/admin/auth/me/email",
                json={"email": "owner.real@example.test", "password": "StrongPassword2026"},
            )
            assert updated_email.status_code == 200
            assert updated_email.json()["email"] == "owner.real@example.test"
            assert client.post(
                "/admin/auth/login",
                json={"email": "owner.real@example.test", "password": "StrongPassword2026"},
            ).status_code == 200
            admin_page = client.get("/admin/")
            assert admin_page.status_code == 200
            assert "Сегменты бизнеса" in admin_page.text
            assert "Аудитории" in admin_page.text
            assert "Не удалось войти:" in admin_page.text
            assert "Сессия не установлена" in admin_page.text
            leads = client.get("/admin/leads?limit=1")
            assert leads.status_code == 200
            payload = leads.json()
            assert payload["limit"] == 1
            assert len(payload["items"]) == 1
            assert payload["items"][0]["conference_code"] == "conference_2026"
            assert payload["items"][0]["display_name"] == "Тестовый Пользователь"
            assert payload["items"][0]["telegram_username"] == "test_owner"
            assert "telegram_user_id" not in str(payload)
            assert "900011" not in str(payload)
            people = client.get("/admin/people?limit=1")
            assert people.status_code == 200
            person_id = people.json()["items"][0]["user_id"]
            assert client.get(f"/admin/people/{person_id}").status_code == 200
            revoked = client.patch(f"/admin/people/{person_id}/marketing-consent", json={"status": "revoked"})
            assert revoked.status_code == 200
            assert revoked.json()["person"]["marketing_consent_status"] == "revoked"
            confirmed = client.patch(f"/admin/people/{person_id}/marketing-consent", json={"status": "confirmed"})
            assert confirmed.json()["person"]["marketing_consent_status"] == "confirmed"
            trace = client.get(f"/admin/logs/people/{person_id}")
            assert trace.status_code == 200
            assert trace.json()["user_id"] == person_id
            dashboard = client.get("/admin/dashboard?days=7")
            assert dashboard.status_code == 200
            assert dashboard.json()["new_people"] == 1
            analytics = client.get("/admin/analytics?days=7")
            assert analytics.status_code == 200
            assert analytics.json()["people"] == 1
            assert analytics.json()["completion_rate"] is None
            assert client.get("/admin/consultations").json()["items"] == []
            assert client.get("/admin/attention").json()["items"] == []
            segments = client.get("/admin/segments")
            assert segments.status_code == 200
            eligible = next(item for item in segments.json()["items"] if item["key"] == "eligible_telegram_broadcast")
            assert eligible["eligible_count"] == 1
            draft = client.post("/admin/broadcasts/drafts", json={"segment_id": eligible["segment_id"], "title": "Черновик", "body": "Только черновик"})
            assert draft.status_code == 201
            assert draft.json()["status"] == "draft"
            broadcast_id = draft.json()["broadcast_id"]
            assert client.get(f"/admin/broadcasts/{broadcast_id}/preview").json()["eligible_count"] == 1
            queued = client.post(f"/admin/broadcasts/{broadcast_id}/confirm-send")
            assert queued.status_code == 200
            assert queued.json()["queued_count"] == 1
            assert client.post(f"/admin/broadcasts/{broadcast_id}/confirm-send").json()["queued_count"] == 1
            assert asyncio.run(_deliver_broadcast(database_url)) == 1
            assert client.get(f"/admin/broadcasts/{broadcast_id}/preview").json()["sent_count"] == 1
            assert client.get("/admin/broadcasts").json()["items"][0]["title"] == "Черновик"
            assert client.post("/admin/auth/logout").status_code == 403
            assert client.post(
                "/admin/auth/logout", headers={"Origin": "http://testserver"}
            ).status_code == 204
            assert client.get("/admin/auth/me").status_code == 401
    finally:
        get_settings.cache_clear()
        asyncio.run(_clear_test_tables(database_url))


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


async def _create_test_lead(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE outbound_messages, lead_bot_sessions, diagnostic_reports, "
                    "diagnostic_sessions, profile_answers, business_profiles, conference_entries, "
                    "events, touchpoints, user_identities, users RESTART IDENTITY CASCADE"
                )
            )
            await ConferenceIntakeService(session).start(
                ConferenceStartCommand(
                    telegram_user_id="900011", qr_code="admin-http-proof",
                    telegram_first_name="Тестовый", telegram_last_name="Пользователь",
                    telegram_username="test_owner",
                )
            )
    finally:
        await factory.kw["bind"].dispose()


async def _enable_broadcast_recipient(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("UPDATE users SET marketing_consent_status = 'confirmed', telegram_reachability = 'allowed', communication_status = 'subscribed'"))
    finally:
        await factory.kw["bind"].dispose()


async def _deliver_broadcast(database_url: str) -> int:
    factory = create_session_factory(database_url)
    try:
        transport = _RecordingTransport()
        delivered = await OutboundWorker(factory, transport).run_once()
        assert len(transport.deliveries) == delivered
        return delivered
    finally:
        await factory.kw["bind"].dispose()


async def _clear_test_tables(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE outbound_messages, lead_bot_sessions, diagnostic_reports, "
                    "diagnostic_sessions, profile_answers, business_profiles, conference_entries, "
                    "events, touchpoints, user_identities, users RESTART IDENTITY CASCADE"
                )
            )
            await session.execute(
                text("TRUNCATE TABLE admin_sessions, admin_users RESTART IDENTITY CASCADE")
            )
    finally:
        await factory.kw["bind"].dispose()
