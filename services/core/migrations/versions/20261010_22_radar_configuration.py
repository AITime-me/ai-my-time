"""Add Demand Radar configuration storage.

Revision ID: 20261010_22
Revises: 20260906_21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261010_22"
down_revision = "20260906_21"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "radar_tenant",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("raw_retention_days", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column(
            "metadata_retention_days", sa.Integer(), nullable=False, server_default=sa.text("90")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_radar_tenant_slug"),
        sa.CheckConstraint("raw_retention_days >= 1", name="ck_radar_tenant_raw_retention_days"),
        sa.CheckConstraint(
            "metadata_retention_days >= 0", name="ck_radar_tenant_metadata_retention_days"
        ),
    )

    op.create_table(
        "radar_tenant_admin",
        _uuid("tenant_id", primary_key=True, nullable=False),
        _uuid("admin_user_id", primary_key=True, nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_tenant_admin_tenant", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["admin_users.id"],
            name="fk_radar_tenant_admin_admin_user",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("role IN ('owner', 'operator')", name="ck_radar_tenant_admin_role"),
    )

    op.create_table(
        "radar_reader",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        sa.Column("reader_key", sa.String(length=128), nullable=False),
        sa.Column("credential_key_id", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_status", sa.String(length=32), nullable=True),
        sa.Column("telegram_authorization_status", sa.String(length=32), nullable=True),
        sa.Column("applied_manifest_version", sa.String(length=64), nullable=True),
        sa.Column("journal_backlog", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_reader_tenant", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_radar_reader_tenant_id"),
        sa.UniqueConstraint("tenant_id", "reader_key", name="uq_radar_reader_tenant_reader_key"),
        sa.UniqueConstraint("credential_key_id", name="uq_radar_reader_credential_key_id"),
        sa.CheckConstraint("journal_backlog >= 0", name="ck_radar_reader_journal_backlog"),
    )
    op.create_index(
        "ix_radar_reader_last_heartbeat_enabled",
        "radar_reader",
        ["last_heartbeat_at"],
        postgresql_where=sa.text("enabled"),
    )

    op.create_table(
        "radar_source",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("reader_id", nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False, server_default="telegram"),
        sa.Column("peer_type", sa.String(length=32), nullable=False),
        sa.Column("peer_id", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "monitoring_capability",
            sa.String(length=32),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_source_tenant", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "reader_id"],
            ["radar_reader.tenant_id", "radar_reader.id"],
            name="fk_radar_source_reader",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_radar_source_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connector",
            "peer_type",
            "peer_id",
            name="uq_radar_source_tenant_connector_peer",
        ),
        sa.CheckConstraint("connector = 'telegram'", name="ck_radar_source_connector"),
        sa.CheckConstraint("peer_id > 0", name="ck_radar_source_peer_id_positive"),
        sa.CheckConstraint(
            "peer_type IN ('channel', 'supergroup', 'group', 'user')",
            name="ck_radar_source_peer_type",
        ),
        sa.CheckConstraint(
            "source_type IN ('channel', 'supergroup', 'group', 'user')",
            name="ck_radar_source_source_type",
        ),
        sa.CheckConstraint(
            "monitoring_capability IN ('realtime', 'history_only', 'unverified')",
            name="ck_radar_source_monitoring_capability",
        ),
    )
    op.create_index(
        "ix_radar_source_tenant_reader_enabled",
        "radar_source",
        ["tenant_id", "reader_id"],
        postgresql_where=sa.text("enabled"),
    )

    op.create_table(
        "radar_destination",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        sa.Column("bot_binding_key", sa.String(length=128), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "verification_state",
            sa.String(length=32),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_destination_tenant",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_radar_destination_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "bot_binding_key",
            "chat_id",
            name="uq_radar_destination_tenant_bot_chat",
        ),
        sa.CheckConstraint(
            "verification_state IN ('unverified', 'pending', 'verified', 'rejected')",
            name="ck_radar_destination_verification_state",
        ),
    )

    op.create_table(
        "radar_search_profile",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _uuid("active_version_id", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_search_profile_tenant",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_radar_search_profile_tenant_id"),
    )

    op.create_table(
        "radar_profile_version",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("profile_id", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rule_schema_version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("freshness_seconds", sa.Integer(), nullable=False, server_default=sa.text("120")),
        sa.Column("normalizer_version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_version_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "profile_id"],
            ["radar_search_profile.tenant_id", "radar_search_profile.id"],
            name="fk_radar_profile_version_profile",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_radar_profile_version_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "profile_id",
            "id",
            name="uq_radar_profile_version_tenant_profile_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "profile_id",
            "version",
            name="uq_radar_profile_version_tenant_profile_version",
        ),
        sa.CheckConstraint("version >= 1", name="ck_radar_profile_version_version"),
        sa.CheckConstraint("freshness_seconds >= 1", name="ck_radar_profile_version_freshness"),
    )

    op.create_foreign_key(
        "fk_radar_search_profile_active_version",
        "radar_search_profile",
        "radar_profile_version",
        ["tenant_id", "id", "active_version_id"],
        ["tenant_id", "profile_id", "id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "radar_search_rule",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("profile_version_id", nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "expression",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["radar_tenant.id"], name="fk_radar_search_rule_tenant", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_search_rule_version",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "profile_version_id",
            "rule_key",
            name="uq_radar_search_rule_tenant_version_key",
        ),
        sa.CheckConstraint("kind IN ('include', 'exclude')", name="ck_radar_search_rule_kind"),
    )

    op.create_table(
        "radar_profile_source",
        _uuid("tenant_id", primary_key=True, nullable=False),
        _uuid("profile_version_id", primary_key=True, nullable=False),
        _uuid("source_id", primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_profile_source_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_id"],
            ["radar_source.tenant_id", "radar_source.id"],
            name="fk_radar_profile_source_source",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_radar_profile_source_tenant_source_version",
        "radar_profile_source",
        ["tenant_id", "source_id", "profile_version_id"],
    )

    op.create_table(
        "radar_profile_destination",
        _uuid("tenant_id", primary_key=True, nullable=False),
        _uuid("profile_version_id", primary_key=True, nullable=False),
        _uuid("destination_id", primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["radar_tenant.id"],
            name="fk_radar_profile_destination_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "profile_version_id"],
            ["radar_profile_version.tenant_id", "radar_profile_version.id"],
            name="fk_radar_profile_destination_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "destination_id"],
            ["radar_destination.tenant_id", "radar_destination.id"],
            name="fk_radar_profile_destination_destination",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_radar_profile_destination_tenant_destination_version",
        "radar_profile_destination",
        ["tenant_id", "destination_id", "profile_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_radar_profile_destination_tenant_destination_version",
        table_name="radar_profile_destination",
    )
    op.drop_table("radar_profile_destination")
    op.drop_index(
        "ix_radar_profile_source_tenant_source_version", table_name="radar_profile_source"
    )
    op.drop_table("radar_profile_source")
    op.drop_table("radar_search_rule")
    op.drop_constraint(
        "fk_radar_search_profile_active_version",
        "radar_search_profile",
        type_="foreignkey",
    )
    op.drop_table("radar_profile_version")
    op.drop_table("radar_search_profile")
    op.drop_table("radar_destination")
    op.drop_index("ix_radar_source_tenant_reader_enabled", table_name="radar_source")
    op.drop_table("radar_source")
    op.drop_index("ix_radar_reader_last_heartbeat_enabled", table_name="radar_reader")
    op.drop_table("radar_reader")
    op.drop_table("radar_tenant_admin")
    op.drop_table("radar_tenant")
