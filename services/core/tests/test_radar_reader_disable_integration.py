"""Reader disable + credential file reload on PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.models import RadarReader, RadarSource, RadarTenant, RadarTenantAdmin
from app.services.admin_auth import AdminAuthService
from app.services.radar_reader_credentials import get_radar_reader_credential_store


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


async def _setup(database_url: str, key: str) -> dict[str, str]:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                __import__("sqlalchemy").text(
                    "TRUNCATE TABLE radar_observation_receipt, radar_source, radar_reader, radar_tenant_admin, "
                    "radar_tenant, admin_sessions, admin_users RESTART IDENTITY CASCADE"
                )
            )
            await AdminAuthService(session).bootstrap_owner(
                email="reload@example.test", password="StrongPassword2026"
            )
            tenant = RadarTenant(slug="reload-tenant")
            session.add(tenant)
            await session.flush()
            reader = RadarReader(
                tenant_id=tenant.id, reader_key="neo", credential_key_id=key
            )
            session.add(reader)
            await session.flush()
            session.add(
                RadarSource(
                    tenant_id=tenant.id,
                    reader_id=reader.id,
                    peer_type="channel",
                    peer_id=42,
                    source_type="channel",
                    is_approved=True,
                    enabled=True,
                    monitoring_capability="realtime",
                )
            )
            return {"reader_id": str(reader.id), "tenant_id": str(tenant.id)}
    finally:
        await factory.kw["bind"].dispose()


def test_secret_reload_and_disabled_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_url = _test_database_url()
    key = "cred-reload-" + secrets.token_hex(4)
    secret = secrets.token_hex(32)
    path = tmp_path / "creds.json"
    path.write_text(json.dumps({key: secret}), encoding="utf-8")
    ids = asyncio.run(_setup(database_url, key))

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ADMIN_TRUSTED_ORIGIN", "http://testserver")
    monkeypatch.setenv("RADAR_READER_CREDENTIALS_PATH", str(path))
    get_settings.cache_clear()
    get_radar_reader_credential_store().clear()

    try:
        with TestClient(create_app()) as client:
            bearer = {"Authorization": f"Bearer {key}.{secret}"}
            assert client.get("/internal/radar/v1/reader-manifest", headers=bearer).status_code == 200

            rotated = secrets.token_hex(32)
            path.write_text(json.dumps({key: rotated}), encoding="utf-8")
            assert client.get("/internal/radar/v1/reader-manifest", headers=bearer).status_code == 401
            assert client.get(
                "/internal/radar/v1/reader-manifest",
                headers={"Authorization": f"Bearer {key}.{rotated}"},
            ).status_code == 200

            async def _disable() -> None:
                factory = create_session_factory(database_url)
                try:
                    async with session_scope(factory) as session:
                        reader = await session.get(RadarReader, uuid.UUID(ids["reader_id"]))
                        assert reader is not None
                        reader.enabled = False
                finally:
                    await factory.kw["bind"].dispose()

            asyncio.run(_disable())
            assert client.get(
                "/internal/radar/v1/reader-manifest",
                headers={"Authorization": f"Bearer {key}.{rotated}"},
            ).status_code == 401
    finally:
        get_settings.cache_clear()
        get_radar_reader_credential_store().clear()
