"""Alembic upgrade/downgrade proofs for Radar Slice 2 and Slice 3 revisions."""

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
SLICE2_HEAD = "20261010_22"
SLICE3_HEAD = "20261010_23"
SLICE4_HEAD = "20261010_24"
REPO_HEAD = "20261010_26"
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


async def _assert_slice2_schema(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert RADAR_TABLES.issubset(present)
    assert await _alembic_version(engine) == SLICE2_HEAD
    async with engine.connect() as conn:
        has_col = (
            await conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'radar_source' AND column_name = 'config_version'
                    """
                )
            )
        ).scalar_one_or_none()
        assert has_col is None


async def _assert_slice3_schema(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert RADAR_TABLES.issubset(present)
    assert await _alembic_version(engine) == SLICE3_HEAD
    async with engine.connect() as conn:
        col = (
            await conn.execute(
                text(
                    """
                    SELECT is_nullable, column_default, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'radar_source' AND column_name = 'config_version'
                    """
                )
            )
        ).one()
        assert col.is_nullable == "NO"
        assert col.data_type == "integer"
        assert "1" in (col.column_default or "")
        check = (
            await conn.execute(
                text(
                    """
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_radar_source_config_version'
                    """
                )
            )
        ).scalar_one()
        assert check == 1


async def _assert_slice4_schema(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert RADAR_TABLES.issubset(present)
    assert await _alembic_version(engine) == SLICE4_HEAD
    async with engine.connect() as conn:
        table = (
            await conn.execute(
                text(
                    "SELECT 1 FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename = 'radar_observation_receipt'"
                )
            )
        ).scalar_one()
        constraint = (
            await conn.execute(
                text(
                    "SELECT 1 FROM pg_constraint "
                    "WHERE conname = 'uq_radar_observation_receipt_tenant_observation'"
                )
            )
        ).scalar_one()
        assert table == 1
        assert constraint == 1


async def _assert_repo_head_schema(engine: AsyncEngine) -> None:
    present = await _public_tables(engine)
    assert RADAR_TABLES.issubset(present)
    assert "radar_observation_receipt" in present
    assert "radar_signal" in present
    assert "radar_alert_outbox" in present
    assert await _alembic_version(engine) == REPO_HEAD


def _restore_head(config: Config) -> None:
    """Always leave the shared CI database on the current repository head."""

    command.upgrade(config, "head")


def test_radar_slice2_configuration_migration_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove historical Slice 2 revision without requiring it to be repo head."""

    async_url = _async_url()
    monkeypatch.setenv("DATABASE_URL", async_url)
    get_settings.cache_clear()

    config = _alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == REPO_HEAD

    try:
        _run(async_url, _reset_schema)

        command.upgrade(config, BASELINE)
        _run(async_url, _assert_baseline_without_radar)

        command.upgrade(config, SLICE2_HEAD)
        _run(async_url, _assert_slice2_schema)
        # Do NOT alembic check here: repository head is ahead of Slice 2.

        command.downgrade(config, BASELINE)
        _run(async_url, _assert_baseline_without_radar)

        command.upgrade(config, SLICE2_HEAD)
        _run(async_url, _assert_slice2_schema)
    finally:
        try:
            _restore_head(config)
        finally:
            get_settings.cache_clear()


def test_radar_slice3_config_version_migration_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove Slice 3/4 historical migrations; alembic check only at repo head."""

    async_url = _async_url()
    monkeypatch.setenv("DATABASE_URL", async_url)
    get_settings.cache_clear()

    config = _alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == REPO_HEAD

    try:
        _run(async_url, _reset_schema)

        command.upgrade(config, SLICE2_HEAD)
        _run(async_url, _assert_slice2_schema)

        command.upgrade(config, SLICE3_HEAD)
        _run(async_url, _assert_slice3_schema)

        command.upgrade(config, SLICE4_HEAD)
        _run(async_url, _assert_slice4_schema)

        command.downgrade(config, SLICE3_HEAD)
        _run(async_url, _assert_slice3_schema)

        command.upgrade(config, SLICE4_HEAD)
        _run(async_url, _assert_slice4_schema)

        command.downgrade(config, SLICE2_HEAD)
        _run(async_url, _assert_slice2_schema)

        command.upgrade(config, SLICE3_HEAD)
        _run(async_url, _assert_slice3_schema)

        command.upgrade(config, "head")
        _run(async_url, _assert_repo_head_schema)
        command.check(config)
    finally:
        try:
            _restore_head(config)
        finally:
            get_settings.cache_clear()
