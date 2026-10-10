"""PostgreSQL proofs for Radar configuration storage and tenant isolation."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import create_session_factory, session_scope
from app.models import (
    RadarDestination,
    RadarProfileDestination,
    RadarProfileSource,
    RadarProfileVersion,
    RadarReader,
    RadarSearchProfile,
    RadarSearchRule,
    RadarSource,
    RadarTenant,
    RadarTenantAdmin,
)
from app.services.admin_auth import AdminAuthService

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

MutateFn = Callable[[AsyncSession], Awaitable[None]]


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


async def _truncate(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_scope(session_factory) as session:
        await session.execute(
            text(
                "TRUNCATE TABLE "
                + ", ".join(RADAR_TABLES)
                + ", admin_sessions, admin_users RESTART IDENTITY CASCADE"
            )
        )


async def _expect_integrity_error(
    session_factory: async_sessionmaker[AsyncSession], mutate: MutateFn
) -> None:
    """Prove a constraint violation in its own transaction (no outer begin conflict)."""

    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await mutate(session)


def test_radar_config_uniques_defaults_and_canonical_peer_id() -> None:
    asyncio.run(_run_storage_basics(_test_database_url()))


def test_radar_tenant_isolation_constraints() -> None:
    asyncio.run(_run_tenant_isolation(_test_database_url()))


async def _run_storage_basics(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    try:
        await _truncate(session_factory)

        async with session_scope(session_factory) as session:
            tenant = RadarTenant(slug="acme")
            session.add(tenant)
            await session.flush()
            assert tenant.raw_retention_days == 30
            assert tenant.metadata_retention_days == 90
            assert tenant.enabled is True
            tenant_id = tenant.id

        async def duplicate_slug(session: AsyncSession) -> None:
            session.add(RadarTenant(slug="acme"))

        await _expect_integrity_error(session_factory, duplicate_slug)

        async with session_scope(session_factory) as session:
            reader = RadarReader(
                tenant_id=tenant_id,
                reader_key="neo-1",
                credential_key_id="cred-1",
            )
            session.add(reader)
            await session.flush()
            reader_id = reader.id

        async def duplicate_reader_key(session: AsyncSession) -> None:
            session.add(
                RadarReader(
                    tenant_id=tenant_id,
                    reader_key="neo-1",
                    credential_key_id="cred-2",
                )
            )

        await _expect_integrity_error(session_factory, duplicate_reader_key)

        async def duplicate_credential_key(session: AsyncSession) -> None:
            session.add(
                RadarReader(
                    tenant_id=tenant_id,
                    reader_key="neo-2",
                    credential_key_id="cred-1",
                )
            )

        await _expect_integrity_error(session_factory, duplicate_credential_key)

        async with session_scope(session_factory) as session:
            source = RadarSource(
                tenant_id=tenant_id,
                reader_id=reader_id,
                peer_type="channel",
                peer_id=1234567890,
                source_type="channel",
                monitoring_capability="realtime",
            )
            session.add(source)
            await session.flush()
            source_id = source.id

        async def duplicate_source_peer(session: AsyncSession) -> None:
            session.add(
                RadarSource(
                    tenant_id=tenant_id,
                    reader_id=reader_id,
                    peer_type="channel",
                    peer_id=1234567890,
                    source_type="channel",
                )
            )

        await _expect_integrity_error(session_factory, duplicate_source_peer)

        async def negative_peer_id(session: AsyncSession) -> None:
            session.add(
                RadarSource(
                    tenant_id=tenant_id,
                    reader_id=reader_id,
                    peer_type="channel",
                    peer_id=-1001234567890,
                    source_type="channel",
                )
            )

        await _expect_integrity_error(session_factory, negative_peer_id)

        async with session_scope(session_factory) as session:
            dest = RadarDestination(
                tenant_id=tenant_id,
                bot_binding_key="ops-bot",
                chat_id=-100555,
            )
            session.add(dest)
            await session.flush()
            dest_id = dest.id

        async def duplicate_destination(session: AsyncSession) -> None:
            session.add(
                RadarDestination(
                    tenant_id=tenant_id,
                    bot_binding_key="ops-bot",
                    chat_id=-100555,
                )
            )

        await _expect_integrity_error(session_factory, duplicate_destination)

        async with session_scope(session_factory) as session:
            profile = RadarSearchProfile(tenant_id=tenant_id, name="Leads")
            session.add(profile)
            await session.flush()
            version = RadarProfileVersion(
                tenant_id=tenant_id, profile_id=profile.id, version=1
            )
            session.add(version)
            await session.flush()
            assert version.freshness_seconds == 120
            profile_id = profile.id
            version_id = version.id

        async def duplicate_version(session: AsyncSession) -> None:
            session.add(
                RadarProfileVersion(
                    tenant_id=tenant_id, profile_id=profile_id, version=1
                )
            )

        await _expect_integrity_error(session_factory, duplicate_version)

        async with session_scope(session_factory) as session:
            session.add(
                RadarSearchRule(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    rule_key="include-crm",
                    kind="include",
                    expression={"terms": ["crm"]},
                )
            )

        async def duplicate_rule_key(session: AsyncSession) -> None:
            session.add(
                RadarSearchRule(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    rule_key="include-crm",
                    kind="exclude",
                    expression={"terms": ["spam"]},
                )
            )

        await _expect_integrity_error(session_factory, duplicate_rule_key)

        async with session_scope(session_factory) as session:
            session.add(
                RadarProfileSource(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    source_id=source_id,
                )
            )
            session.add(
                RadarProfileDestination(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    destination_id=dest_id,
                )
            )

        async def duplicate_profile_source(session: AsyncSession) -> None:
            session.add(
                RadarProfileSource(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    source_id=source_id,
                )
            )

        await _expect_integrity_error(session_factory, duplicate_profile_source)

        async def duplicate_profile_destination(session: AsyncSession) -> None:
            session.add(
                RadarProfileDestination(
                    tenant_id=tenant_id,
                    profile_version_id=version_id,
                    destination_id=dest_id,
                )
            )

        await _expect_integrity_error(session_factory, duplicate_profile_destination)
    finally:
        try:
            await _truncate(session_factory)
        finally:
            await session_factory.kw["bind"].dispose()


async def _run_tenant_isolation(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    try:
        await _truncate(session_factory)
        async with session_scope(session_factory) as session:
            owner = await AdminAuthService(session).bootstrap_owner(
                email="radar-owner@example.test", password="StrongPassword2026"
            )
            tenant_a = RadarTenant(slug="tenant-a")
            tenant_b = RadarTenant(slug="tenant-b")
            session.add_all([tenant_a, tenant_b])
            await session.flush()
            session.add(
                RadarTenantAdmin(
                    tenant_id=tenant_a.id,
                    admin_user_id=owner.user_id,
                    role="owner",
                )
            )
            reader_a = RadarReader(
                tenant_id=tenant_a.id, reader_key="r-a", credential_key_id="cred-a"
            )
            reader_b = RadarReader(
                tenant_id=tenant_b.id, reader_key="r-b", credential_key_id="cred-b"
            )
            session.add_all([reader_a, reader_b])
            await session.flush()
            source_a = RadarSource(
                tenant_id=tenant_a.id,
                reader_id=reader_a.id,
                peer_type="channel",
                peer_id=111,
                source_type="channel",
            )
            source_b = RadarSource(
                tenant_id=tenant_b.id,
                reader_id=reader_b.id,
                peer_type="channel",
                peer_id=333,
                source_type="channel",
            )
            dest_a = RadarDestination(
                tenant_id=tenant_a.id, bot_binding_key="bot", chat_id=-1001
            )
            dest_b = RadarDestination(
                tenant_id=tenant_b.id, bot_binding_key="bot", chat_id=-1002
            )
            profile_a = RadarSearchProfile(tenant_id=tenant_a.id, name="A")
            profile_b = RadarSearchProfile(tenant_id=tenant_b.id, name="B")
            session.add_all([source_a, source_b, dest_a, dest_b, profile_a, profile_b])
            await session.flush()
            version_a = RadarProfileVersion(
                tenant_id=tenant_a.id, profile_id=profile_a.id, version=1
            )
            version_b = RadarProfileVersion(
                tenant_id=tenant_b.id, profile_id=profile_b.id, version=1
            )
            session.add_all([version_a, version_b])
            await session.flush()
            ids = {
                "tenant_a": tenant_a.id,
                "tenant_b": tenant_b.id,
                "reader_b": reader_b.id,
                "source_b": source_b.id,
                "dest_b": dest_b.id,
                "profile_a": profile_a.id,
                "profile_b": profile_b.id,
                "version_a": version_a.id,
                "version_b": version_b.id,
            }

        async def cross_tenant_reader(session: AsyncSession) -> None:
            session.add(
                RadarSource(
                    tenant_id=ids["tenant_a"],
                    reader_id=ids["reader_b"],
                    peer_type="channel",
                    peer_id=222,
                    source_type="channel",
                )
            )

        await _expect_integrity_error(session_factory, cross_tenant_reader)

        async def cross_tenant_source_binding(session: AsyncSession) -> None:
            session.add(
                RadarProfileSource(
                    tenant_id=ids["tenant_a"],
                    profile_version_id=ids["version_a"],
                    source_id=ids["source_b"],
                )
            )

        await _expect_integrity_error(session_factory, cross_tenant_source_binding)

        async def cross_tenant_destination_binding(session: AsyncSession) -> None:
            session.add(
                RadarProfileDestination(
                    tenant_id=ids["tenant_a"],
                    profile_version_id=ids["version_a"],
                    destination_id=ids["dest_b"],
                )
            )

        await _expect_integrity_error(session_factory, cross_tenant_destination_binding)

        async def version_wrong_profile(session: AsyncSession) -> None:
            session.add(
                RadarProfileVersion(
                    tenant_id=ids["tenant_a"],
                    profile_id=ids["profile_b"],
                    version=2,
                )
            )

        await _expect_integrity_error(session_factory, version_wrong_profile)

        # Deferred active_version FK is checked at COMMIT.
        async def active_version_wrong_profile(session: AsyncSession) -> None:
            profile_a = await session.get(RadarSearchProfile, ids["profile_a"])
            assert profile_a is not None
            profile_a.active_version_id = ids["version_b"]

        await _expect_integrity_error(session_factory, active_version_wrong_profile)

        async def active_version_wrong_tenant(session: AsyncSession) -> None:
            # Same composite FK path: version_b belongs to tenant_b / profile_b.
            profile_a = await session.get(RadarSearchProfile, ids["profile_a"])
            assert profile_a is not None
            profile_a.active_version_id = ids["version_b"]

        await _expect_integrity_error(session_factory, active_version_wrong_tenant)

        async def rule_cross_tenant_version(session: AsyncSession) -> None:
            session.add(
                RadarSearchRule(
                    tenant_id=ids["tenant_a"],
                    profile_version_id=ids["version_b"],
                    rule_key="x",
                    kind="include",
                    expression={},
                )
            )

        await _expect_integrity_error(session_factory, rule_cross_tenant_version)

        # Positive control: same-tenant active_version pointer succeeds.
        async with session_scope(session_factory) as session:
            profile_a = await session.get(RadarSearchProfile, ids["profile_a"])
            assert profile_a is not None
            profile_a.active_version_id = ids["version_a"]
            version_a = await session.get(RadarProfileVersion, ids["version_a"])
            assert version_a is not None
            version_a.activated_at = version_a.created_at
    finally:
        try:
            await _truncate(session_factory)
        finally:
            await session_factory.kw["bind"].dispose()
