"""Initial conference identity, attribution, and event core.

Revision ID: 20260826_01
Revises:
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_01"
down_revision = None
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "users",
        _uuid_column("id", primary_key=True, nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=40), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "user_identities",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("connection_scope", sa.String(length=128), nullable=False),
        sa.Column("external_id", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("provider", "connection_scope", "external_id", name="uq_user_identities_provider_scope_external_id"),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
    op.create_table(
        "touchpoints",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("source_code", sa.String(length=80), nullable=False),
        sa.Column("entry_code", sa.String(length=160), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_touchpoints_user_observed_at", "touchpoints", ["user_id", "observed_at"])
    op.create_index("ix_touchpoints_source_code", "touchpoints", ["source_code"])
    op.create_table(
        "events",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_events_user_occurred_at", "events", ["user_id", "occurred_at"])
    op.create_index("ix_events_kind_occurred_at", "events", ["kind", "occurred_at"])
    op.create_table(
        "conference_entries",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("conference_code", sa.String(length=80), nullable=False),
        sa.Column("qr_code", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="started"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "conference_code", name="uq_conference_entries_user_code"),
    )
    op.create_index("ix_conference_entries_code_created_at", "conference_entries", ["conference_code", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_conference_entries_code_created_at", table_name="conference_entries")
    op.drop_table("conference_entries")
    op.drop_index("ix_events_kind_occurred_at", table_name="events")
    op.drop_index("ix_events_user_occurred_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_touchpoints_source_code", table_name="touchpoints")
    op.drop_index("ix_touchpoints_user_observed_at", table_name="touchpoints")
    op.drop_table("touchpoints")
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_table("users")
