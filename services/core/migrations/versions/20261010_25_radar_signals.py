"""Add durable Demand Radar tenant signals.

Revision ID: 20261010_25
Revises: 20261010_24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261010_25"
down_revision = "20261010_24"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_radar_observation_receipt_tenant_id",
        "radar_observation_receipt",
        ["tenant_id", "id"],
    )
    op.create_table(
        "radar_signal",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("observation_receipt_id", nullable=False),
        _uuid("profile_version_id", nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("matched_rule_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("excluded_rule_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("freshness_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["radar_tenant.id"], name="fk_radar_signal_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "observation_receipt_id"], ["radar_observation_receipt.tenant_id", "radar_observation_receipt.id"], name="fk_radar_signal_receipt", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "profile_version_id"], ["radar_profile_version.tenant_id", "radar_profile_version.id"], name="fk_radar_signal_profile_version", ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "observation_receipt_id", name="uq_radar_signal_tenant_receipt"),
        sa.CheckConstraint("status IN ('pending', 'matched', 'excluded', 'no_match', 'stale', 'deleted')", name="ck_radar_signal_status"),
    )
    op.create_index("ix_radar_signal_tenant_status_created", "radar_signal", ["tenant_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_radar_signal_tenant_status_created", table_name="radar_signal")
    op.drop_table("radar_signal")
    op.drop_constraint(
        "uq_radar_observation_receipt_tenant_id",
        "radar_observation_receipt",
        type_="unique",
    )
