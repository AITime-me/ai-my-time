"""Unit registration checks for Radar configuration models (no DB required)."""

from __future__ import annotations

from app.db.base import Base
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


def _constraint_names(table_name: str) -> set[str | None]:
    table = Base.metadata.tables[table_name]
    return {getattr(c, "name", None) for c in table.constraints}


def _index_names(table_name: str) -> set[str | None]:
    table = Base.metadata.tables[table_name]
    return {idx.name for idx in table.indexes}


def test_radar_config_tables_registered_in_metadata() -> None:
    expected = {
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
    assert expected.issubset(set(Base.metadata.tables))


def test_radar_source_peer_id_is_bigint_positive_check() -> None:
    table = Base.metadata.tables["radar_source"]
    assert "BIGINT" in str(table.c.peer_id.type).upper()
    names = _constraint_names("radar_source")
    assert "ck_radar_source_peer_id_positive" in names
    assert "ck_radar_source_connector" in names
    assert "ck_radar_source_config_version" in names
    assert "config_version" in table.c
    assert "uq_radar_source_tenant_connector_peer" in names
    assert "uq_radar_source_tenant_id" in names
    assert "ix_radar_source_tenant_reader_enabled" in _index_names("radar_source")


def test_radar_reader_uniques_and_heartbeat_index() -> None:
    names = _constraint_names("radar_reader")
    assert "uq_radar_reader_tenant_reader_key" in names
    assert "uq_radar_reader_credential_key_id" in names
    assert "uq_radar_reader_tenant_id" in names
    assert "ix_radar_reader_last_heartbeat_enabled" in _index_names("radar_reader")


def test_radar_destination_unique_constraint() -> None:
    names = _constraint_names("radar_destination")
    assert "uq_radar_destination_tenant_bot_chat" in names
    assert "uq_radar_destination_tenant_id" in names
    table = Base.metadata.tables["radar_destination"]
    assert "BIGINT" in str(table.c.chat_id.type).upper()


def test_radar_profile_version_and_rule_uniques() -> None:
    assert "uq_radar_profile_version_tenant_profile_version" in _constraint_names(
        "radar_profile_version"
    )
    assert "uq_radar_profile_version_tenant_profile_id" in _constraint_names(
        "radar_profile_version"
    )
    assert "uq_radar_search_rule_tenant_version_key" in _constraint_names("radar_search_rule")
    expression = Base.metadata.tables["radar_search_rule"].c.expression
    assert "JSONB" in str(expression.type).upper()


def test_radar_profile_bindings_have_reverse_indexes() -> None:
    assert "ix_radar_profile_source_tenant_source_version" in _index_names(
        "radar_profile_source"
    )
    assert "ix_radar_profile_destination_tenant_destination_version" in _index_names(
        "radar_profile_destination"
    )


def test_radar_profile_active_version_fk_is_deferred() -> None:
    table = Base.metadata.tables["radar_search_profile"]
    fks = [
        fk
        for fk in table.foreign_key_constraints
        if fk.name == "fk_radar_search_profile_active_version"
    ]
    assert len(fks) == 1
    assert fks[0].deferrable is True
    assert fks[0].initially == "DEFERRED"


def test_radar_tenant_slug_unique_and_retention_checks() -> None:
    names = _constraint_names("radar_tenant")
    assert "uq_radar_tenant_slug" in names
    assert "ck_radar_tenant_raw_retention_days" in names
    assert "ck_radar_tenant_metadata_retention_days" in names


def test_radar_model_exports_exist() -> None:
    assert RadarTenant.__tablename__ == "radar_tenant"
    assert RadarTenantAdmin.__tablename__ == "radar_tenant_admin"
    assert RadarReader.__tablename__ == "radar_reader"
    assert RadarSource.__tablename__ == "radar_source"
    assert RadarDestination.__tablename__ == "radar_destination"
    assert RadarSearchProfile.__tablename__ == "radar_search_profile"
    assert RadarProfileVersion.__tablename__ == "radar_profile_version"
    assert RadarSearchRule.__tablename__ == "radar_search_rule"
    assert RadarProfileSource.__tablename__ == "radar_profile_source"
    assert RadarProfileDestination.__tablename__ == "radar_profile_destination"


def test_no_credential_secret_columns_on_reader() -> None:
    columns = set(Base.metadata.tables["radar_reader"].c.keys())
    forbidden = {
        "token",
        "session",
        "session_string",
        "api_hash",
        "password",
        "secret",
        "credential",
        "bot_token",
    }
    assert "credential_key_id" in columns
    assert columns.isdisjoint(forbidden)
