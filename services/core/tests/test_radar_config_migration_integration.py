"""Alembic upgrade/downgrade/re-upgrade for Radar configuration revision."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

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


def _async_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def _sync_url(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


def test_radar_configuration_migration_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    async_url = _async_url()
    sync_url = _sync_url(async_url)
    # env.py reads DATABASE_URL via settings, not alembic.ini sqlalchemy.url.
    monkeypatch.setenv("DATABASE_URL", async_url)
    get_settings.cache_clear()

    config = _alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == RADAR_HEAD

    engine = create_engine(sync_url)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

        command.upgrade(config, BASELINE)
        with engine.connect() as conn:
            present = {
                row[0]
                for row in conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            }
            assert "users" in present
            assert RADAR_TABLES.isdisjoint(present)
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert version == BASELINE

        command.upgrade(config, RADAR_HEAD)
        with engine.connect() as conn:
            present = {
                row[0]
                for row in conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            }
            assert RADAR_TABLES.issubset(present)
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert version == RADAR_HEAD
            peer_check = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'ck_radar_source_peer_id_positive'
                    """
                )
            ).scalar_one()
            assert peer_check == 1
            deferred = conn.execute(
                text(
                    """
                    SELECT confdeltype, condeferrable, condeferred
                    FROM pg_constraint
                    WHERE conname = 'fk_radar_search_profile_active_version'
                    """
                )
            ).one()
            assert deferred.condeferrable is True
            assert deferred.condeferred is True

        command.check(config)

        command.downgrade(config, BASELINE)
        with engine.connect() as conn:
            present = {
                row[0]
                for row in conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            }
            assert RADAR_TABLES.isdisjoint(present)
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert version == BASELINE

        command.upgrade(config, RADAR_HEAD)
        with engine.connect() as conn:
            present = {
                row[0]
                for row in conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            }
            assert RADAR_TABLES.issubset(present)
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert version == RADAR_HEAD

        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()
