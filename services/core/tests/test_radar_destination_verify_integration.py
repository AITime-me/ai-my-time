"""Regression: verify_destination must not raise MissingGreenlet after flush."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import AdminAuditEvent, RadarDestination, RadarTenant
from app.schemas.radar_admin import RadarDestinationCreate
from app.services.admin_auth import AdminAuthService
from app.services.radar_config import RadarConfigService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_verify_destination_refreshes_before_view_and_is_idempotent() -> None:
    asyncio.run(_run(_test_database_url()))


async def _run(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE admin_audit_events, admin_sessions, admin_users, "
                    "radar_destination, radar_tenant RESTART IDENTITY CASCADE"
                )
            )
            owner = await AdminAuthService(session).bootstrap_owner(
                email="dest-verify@example.test", password="StrongPassword2026"
            )
            actor_id = owner.user_id
            tenant = RadarTenant(slug="dest-verify")
            session.add(tenant)
            await session.flush()

            service = RadarConfigService(session)
            created = await service.create_destination(
                actor_id=actor_id,
                tenant_id=tenant.id,
                payload=RadarDestinationCreate(
                    bot_binding_key="aimytime-radar-bot",
                    chat_id=1213125969,
                ),
            )
            assert created.verification_state == "unverified"
            assert created.verified_at is None

            verified = await service.verify_destination(
                actor_id=actor_id,
                tenant_id=tenant.id,
                destination_id=created.id,
            )
            assert verified.verification_state == "verified"
            assert verified.verified_at is not None
            assert verified.updated_at is not None
            assert verified.chat_id == 1213125969
            assert verified.bot_binding_key == "aimytime-radar-bot"

            audits = list(
                await session.scalars(
                    select(AdminAuditEvent).where(
                        AdminAuditEvent.action == "radar.destination.verified",
                        AdminAuditEvent.object_id == created.id,
                    )
                )
            )
            assert len(audits) == 1

            again = await service.verify_destination(
                actor_id=actor_id,
                tenant_id=tenant.id,
                destination_id=created.id,
            )
            assert again.verification_state == "verified"
            assert again.verified_at == verified.verified_at

            row = await session.get(RadarDestination, created.id)
            assert row is not None
            assert row.verification_state == "verified"
            assert row.verified_at is not None

            audits_after = list(
                await session.scalars(
                    select(AdminAuditEvent).where(
                        AdminAuditEvent.action == "radar.destination.verified",
                        AdminAuditEvent.object_id == created.id,
                    )
                )
            )
            assert len(audits_after) == 1
    finally:
        await factory.kw["bind"].dispose()
