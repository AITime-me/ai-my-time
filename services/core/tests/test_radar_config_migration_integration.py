"""Alembic upgrade/downgrade/re-upgrade for Radar configuration revision."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.settings import get_settings

BASELINE = "20260906_21"
RADAR_HEAD = "20261010_22"
RADAR_TABLES = {
    "radar_tenant",
    "radar_tenant_admin",
    "radar_reader",
    "radar_source",
    "radar_destination",
    "radar_search_profile",
    "radar_profile_version",
    "radar_search_rule",
    "radar_profile_source",
    "radar_profile_destination",
}

T = TypeVar("T")


def _async_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


async def _with_engine(
    database_url: str, operation: Callable[[AsyncEngine], Awaitable[T]]
) -> T:
    """One AsyncEngine per asyncio.run — matches Core asyncpg usage."""

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        return await operation(engine)
    finally:
        await engine.dispose()


def _run(database_url: str, operation: Callable[[AsyncEngine], Awaitable[T]]) -> T:
    return asyncio.run(_with_engine(database_url, operation))


async def _reset_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))


async def _public_tables(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
        ).all()
    return {row[0] for row in rows}


async def _alembic_version(engine: AsyncEngine) -> str:
    async with engine.connect() as conn:
        return (
            await conn.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()


async def _assert_baseline_without_radar(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert "users" in present
    assert RADAR_TABLES.isdisjoint(present)
    assert await _alembic_version(engine) == BASELINE


async def _assert_radar_schema_present(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert RADAR_TABLES.issubset(present)
    assert await _alembic_version(engine) == RADAR_HEAD

    async with engine.connect() as conn:
        peer_check = (
            await conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'ck_radar_source_peer_id_positive'
                    """
                )
            )
        ).scalar_one()
        assert peer_check == 1
        deferred = (
            await conn.execute(
                text(
                    """
                    SELECT condeferrable, condeferred
                    FROM pg_constraint
                    WHERE conname = 'fk_radar_search_profile_active_version'
                    """
                )
            )
        ).one()
        assert deferred.condeferrable is True
        assert deferred.condeferred is True


def test_radar_configuration_migration_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    async_url = _async_url()
    # env.py / CI use DATABASE_URL with postgresql+asyncpg:// (no sync psycopg).
    monkeypatch.setenv("DATABASE_URL", async_url)
    get_settings.cache_clear()

    config = _alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == RADAR_HEAD

    try:
        _run(async_url, _reset_schema)

        command.upgrade(config, BASELINE)
        _run(async_url, _assert_baseline_without_radar)

        command.upgrade(config, RADAR_HEAD)
        _run(async_url, _assert_radar_schema_present)
        command.check(config)

        command.downgrade(config, BASELINE)
        _run(async_url, _assert_baseline_without_radar)

        command.upgrade(config, RADAR_HEAD)
        _run(async_url, _assert_radar_schema_present)

        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()
