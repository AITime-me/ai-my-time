"""PostgreSQL HTTP proofs for Radar headless config API + Reader manifest."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope
from app.main import create_app
from app.models import RadarReader, RadarTenant, RadarTenantAdmin
from app.radar_assets import load_fixture
from app.schemas.radar_fingerprint import compute_revision_fingerprint
from app.schemas.radar_v1 import RadarObservationV1
from app.services.admin_auth import AdminAuthService
from app.services.radar_reader_credentials import get_radar_reader_credential_store

RADAR_TABLES = (
    "radar_signal",
    "radar_observation_receipt",
    "radar_profile_destination",
    "radar_profile_source",
    "radar_search_rule",
    "radar_profile_version",
    "radar_search_profile",
    "radar_destination",
    "radar_source",
    "radar_reader",
    "radar_tenant_admin",
    "radar_tenant",
)


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


async def _truncate(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE "
                    + ", ".join(RADAR_TABLES)
                    + ", admin_audit_events, admin_sessions, admin_users RESTART IDENTITY CASCADE"
                )
            )
    finally:
        await factory.kw["bind"].dispose()


async def _seed(database_url: str, *, cred_a: str, cred_b: str) -> dict[str, str]:
    from app.models import AdminUser
    from app.services.admin_auth import _hash_password

    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            owner = await AdminAuthService(session).bootstrap_owner(
                email="radar-api-owner@example.test", password="StrongPassword2026"
            )
            session.add(
                AdminUser(
                    email="outsider@example.test",
                    password_hash=_hash_password("StrongPassword2026"),
                    role="manager",
                )
            )
            tenant_a = RadarTenant(slug="tenant-api-a")
            tenant_b = RadarTenant(slug="tenant-api-b")
            session.add_all([tenant_a, tenant_b])
            await session.flush()
            session.add(
                RadarTenantAdmin(
                    tenant_id=tenant_a.id, admin_user_id=owner.user_id, role="owner"
                )
            )
            reader_a = RadarReader(
                tenant_id=tenant_a.id, reader_key="reader-a", credential_key_id=cred_a
            )
            reader_b = RadarReader(
                tenant_id=tenant_b.id, reader_key="reader-b", credential_key_id=cred_b
            )
            session.add_all([reader_a, reader_b])
            await session.flush()
            return {
                "tenant_a": str(tenant_a.id),
                "tenant_b": str(tenant_b.id),
                "reader_a": str(reader_a.id),
                "reader_b": str(reader_b.id),
                "owner_email": "radar-api-owner@example.test",
                "outsider_email": "outsider@example.test",
            }
    finally:
        await factory.kw["bind"].dispose()


def _client(monkeypatch: pytest.MonkeyPatch, database_url: str, creds_path: Path) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ADMIN_TRUSTED_ORIGIN", "http://testserver")
    monkeypatch.setenv("RADAR_READER_CREDENTIALS_PATH", str(creds_path))
    get_settings.cache_clear()
    get_radar_reader_credential_store().clear()
    return TestClient(create_app())


def _auth_headers(tenant_id: str) -> dict[str, str]:
    return {
        "Origin": "http://testserver",
        "Content-Type": "application/json",
        "X-Radar-Tenant-Id": tenant_id,
    }


def test_radar_headless_config_api_and_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_url = _test_database_url()
    asyncio.run(_truncate(database_url))
    secret_a = secrets.token_hex(32)
    secret_b = secrets.token_hex(32)
    key_a = "cred-a-" + secrets.token_hex(4)
    key_b = "cred-b-" + secrets.token_hex(4)
    creds_path = tmp_path / "reader-creds.json"
    creds_path.write_text(json.dumps({key_a: secret_a, key_b: secret_b}), encoding="utf-8")
    ids = asyncio.run(_seed(database_url, cred_a=key_a, cred_b=key_b))

    try:
        with _client(monkeypatch, database_url, creds_path) as client:
            # unauthenticated
            assert client.get(
                "/admin/radar/sources", headers={"X-Radar-Tenant-Id": ids["tenant_a"]}
            ).status_code == 401

            # outsider login without membership
            assert client.post(
                "/admin/auth/login",
                json={"email": ids["outsider_email"], "password": "StrongPassword2026"},
            ).status_code == 200
            assert client.get(
                "/admin/radar/sources", headers={"X-Radar-Tenant-Id": ids["tenant_a"]}
            ).status_code == 404
            client.post("/admin/auth/logout", headers={"Origin": "http://testserver"})

            login = client.post(
                "/admin/auth/login",
                json={"email": ids["owner_email"], "password": "StrongPassword2026"},
            )
            assert login.status_code == 200
            headers = _auth_headers(ids["tenant_a"])

            # Origin guard
            assert client.post(
                "/admin/radar/sources",
                headers={"X-Radar-Tenant-Id": ids["tenant_a"], "Content-Type": "application/json"},
                json={
                    "peer_type": "channel",
                    "peer_id": 1,
                    "source_type": "channel",
                    "reader_id": ids["reader_a"],
                    "is_approved": True,
                },
            ).status_code == 403
            assert client.post(
                "/admin/radar/sources",
                headers={**headers, "Origin": "https://evil.example"},
                json={
                    "peer_type": "channel",
                    "peer_id": 1,
                    "source_type": "channel",
                    "reader_id": ids["reader_a"],
                },
            ).status_code == 403

            # create source
            created = client.post(
                "/admin/radar/sources",
                headers=headers,
                json={
                    "peer_type": "channel",
                    "peer_id": 1234567890,
                    "source_type": "channel",
                    "reader_id": ids["reader_a"],
                    "is_approved": True,
                    "enabled": True,
                    "monitoring_capability": "realtime",
                },
            )
            assert created.status_code == 201, created.text
            source = created.json()
            assert source["config_version"] == 1
            source_id = source["id"]

            # negative peer rejected
            assert client.post(
                "/admin/radar/sources",
                headers=headers,
                json={
                    "peer_type": "channel",
                    "peer_id": -100123,
                    "source_type": "channel",
                    "reader_id": ids["reader_a"],
                },
            ).status_code == 422

            # duplicate identity
            assert client.post(
                "/admin/radar/sources",
                headers=headers,
                json={
                    "peer_type": "channel",
                    "peer_id": 1234567890,
                    "source_type": "channel",
                    "reader_id": ids["reader_a"],
                },
            ).status_code == 409

            # foreign reader
            assert client.post(
                "/admin/radar/sources",
                headers=headers,
                json={
                    "peer_type": "channel",
                    "peer_id": 999,
                    "source_type": "channel",
                    "reader_id": ids["reader_b"],
                },
            ).status_code == 404

            # identity mutation rejected by schema
            assert client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"expected_config_version": 1, "peer_id": 1},
            ).status_code == 422

            # CAS success
            patched = client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"expected_config_version": 1, "title": "Main"},
            )
            assert patched.status_code == 200
            assert patched.json()["config_version"] == 2
            assert patched.json()["title"] == "Main"

            # stale CAS
            stale = client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"expected_config_version": 1, "title": "Stale"},
            )
            assert stale.status_code == 409
            assert stale.json()["detail"] == "source_version_conflict"
            assert client.get(
                "/admin/radar/sources", headers={"X-Radar-Tenant-Id": ids["tenant_a"]}
            ).json()["items"][0]["title"] == "Main"

            # missing expected version
            assert client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"enabled": False},
            ).status_code == 422

            # cross-tenant source
            assert client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=_auth_headers(ids["tenant_b"]),
                json={"expected_config_version": 2, "enabled": False},
            ).status_code == 404

            # destination unverified
            dest = client.post(
                "/admin/radar/destinations",
                headers=headers,
                json={"bot_binding_key": "ops", "chat_id": -1001},
            )
            assert dest.status_code == 201
            assert dest.json()["verification_state"] == "unverified"
            assert dest.json()["verified_at"] is None
            assert client.post(
                "/admin/radar/destinations",
                headers=headers,
                json={
                    "bot_binding_key": "ops2",
                    "chat_id": -1002,
                    "verification_state": "verified",
                },
            ).status_code == 422
            dest_id = dest.json()["id"]

            verified = client.post(
                f"/admin/radar/destinations/{dest_id}/verify",
                headers=headers,
            )
            assert verified.status_code == 200, verified.text
            assert verified.json()["verification_state"] == "verified"
            assert verified.json()["verified_at"] is not None
            assert client.post(
                f"/admin/radar/destinations/{dest_id}/verify",
                headers=headers,
            ).status_code == 200

            # profile + version
            profile = client.post(
                "/admin/radar/profiles",
                headers=headers,
                json={"name": "Leads"},
            )
            assert profile.status_code == 201
            profile_id = profile.json()["id"]
            version = client.post(
                f"/admin/radar/profiles/{profile_id}/versions",
                headers=headers,
                json={
                    "rules": [
                        {
                            "rule_key": "include-crm",
                            "kind": "include",
                            "expression": {"terms": ["crm"]},
                        }
                    ],
                    "source_ids": [source_id],
                    "destination_ids": [dest_id],
                },
            )
            assert version.status_code == 201, version.text
            version_id = version.json()["id"]
            assert version.json()["version"] == 1

            # duplicate rule keys
            assert client.post(
                f"/admin/radar/profiles/{profile_id}/versions",
                headers=headers,
                json={
                    "rules": [
                        {"rule_key": "x", "kind": "include", "expression": {}},
                        {"rule_key": "x", "kind": "exclude", "expression": {}},
                    ],
                    "source_ids": [source_id],
                    "destination_ids": [dest_id],
                },
            ).status_code == 409

            # activate
            activated = client.post(
                f"/admin/radar/profiles/{profile_id}/activate",
                headers=headers,
                json={"version_id": version_id},
            )
            assert activated.status_code == 200
            assert activated.json()["active_version_id"] == version_id
            # idempotent
            assert client.post(
                f"/admin/radar/profiles/{profile_id}/activate",
                headers=headers,
                json={"version_id": version_id},
            ).status_code == 200

            # readers projection
            readers = client.get(
                "/admin/radar/readers", headers={"X-Radar-Tenant-Id": ids["tenant_a"]}
            )
            assert readers.status_code == 200
            assert readers.json()["items"][0]["credential_key_id"] == key_a
            body = readers.text
            assert secret_a not in body

            # Reader cannot use Admin session for manifest
            assert client.get("/internal/radar/v1/reader-manifest").status_code == 401

            # Reader bearer alone cannot call Admin.  This needs a fresh client:
            # the owner session above remains valid and is the only credential
            # accepted by the Admin route.
            bearer = {"Authorization": f"Bearer {key_a}.{secret_a}"}
            with TestClient(create_app()) as reader_client:
                assert reader_client.get(
                    "/admin/radar/sources",
                    headers={**bearer, "X-Radar-Tenant-Id": ids["tenant_a"]},
                ).status_code == 401

            # An unrelated Reader Authorization header must not replace an
            # otherwise valid Admin browser session on an Admin endpoint.
            assert client.get(
                "/admin/radar/sources",
                headers={**bearer, "X-Radar-Tenant-Id": ids["tenant_a"]},
            ).status_code == 200

            # Manifest
            manifest = client.get("/internal/radar/v1/reader-manifest", headers=bearer)
            assert manifest.status_code == 200, manifest.text
            payload = manifest.json()
            assert payload["schema_version"] == 1
            assert payload["reader_id"] == ids["reader_a"]
            assert payload["sources"][0]["peer_id"] == "1234567890"
            assert payload["sources"][0]["monitoring_capability"] == "realtime"
            assert "rules" not in payload
            assert "destinations" not in str(payload)
            assert secret_a not in manifest.text
            version_one = payload["manifest_version"]
            stable = client.get("/internal/radar/v1/reader-manifest", headers=bearer).json()
            assert stable["manifest_version"] == version_one

            observation = load_fixture("observation.live_upsert.json")
            observation["source_id"] = source_id
            observation["manifest_version"] = version_one
            parsed_observation = RadarObservationV1.model_validate(observation)
            observation["revision_fingerprint"] = compute_revision_fingerprint(parsed_observation)
            accepted = client.post(
                "/internal/radar/v1/observations", headers=bearer, json=observation
            )
            assert accepted.status_code == 201, accepted.text
            assert accepted.json()["status"] == "accepted"
            duplicate = client.post(
                "/internal/radar/v1/observations", headers=bearer, json=observation
            )
            assert duplicate.status_code == 201, duplicate.text
            assert duplicate.json()["status"] == "duplicate"
            assert duplicate.json()["receipt_id"] == accepted.json()["receipt_id"]

            # wrong secret / unknown key / other reader
            assert client.get(
                "/internal/radar/v1/reader-manifest",
                headers={"Authorization": f"Bearer {key_a}.wrong"},
            ).status_code == 401
            assert client.get(
                "/internal/radar/v1/reader-manifest",
                headers={"Authorization": f"Bearer unknown.{secret_a}"},
            ).status_code == 401
            assert client.get(
                "/internal/radar/v1/reader-manifest",
                headers={"Authorization": f"Bearer {key_b}.{secret_b}"},
            ).status_code == 404  # no sources for reader B

            # disable source -> absent from manifest + version bump
            disabled = client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"expected_config_version": 2, "enabled": False},
            )
            assert disabled.status_code == 200
            assert disabled.json()["config_version"] == 3
            assert client.get(
                "/internal/radar/v1/reader-manifest", headers=bearer
            ).status_code == 404

            # re-enable changes manifest version
            enabled = client.patch(
                f"/admin/radar/sources/{source_id}",
                headers=headers,
                json={"expected_config_version": 3, "enabled": True},
            )
            assert enabled.status_code == 200
            again = client.get("/internal/radar/v1/reader-manifest", headers=bearer).json()
            assert again["manifest_version"] != version_one

            # credential store unavailable
            monkeypatch.setenv("RADAR_READER_CREDENTIALS_PATH", str(tmp_path / "missing.json"))
            get_settings.cache_clear()
            get_radar_reader_credential_store().clear()
            with TestClient(create_app()) as client2:
                # re-login not needed for reader
                assert client2.get(
                    "/internal/radar/v1/reader-manifest", headers=bearer
                ).status_code == 503
    finally:
        get_settings.cache_clear()
        get_radar_reader_credential_store().clear()
        asyncio.run(_truncate(database_url))
