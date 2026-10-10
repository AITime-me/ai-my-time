"""Add durable Demand Radar Reader observation receipts.

Revision ID: 20261010_24
Revises: 20261010_23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261010_24"
down_revision = "20261010_23"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "radar_observation_receipt",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("reader_id", nullable=False),
        _uuid("source_id", nullable=False),
        _uuid("observation_id", nullable=False),
        sa.Column("manifest_version", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=32), nullable=False),
        sa.Column("revision_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("event_kind", sa.String(length=32), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["radar_tenant.id"], name="fk_radar_observation_receipt_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "reader_id"], ["radar_reader.tenant_id", "radar_reader.id"], name="fk_radar_observation_receipt_reader", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "source_id"], ["radar_source.tenant_id", "radar_source.id"], name="fk_radar_observation_receipt_source", ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "observation_id", name="uq_radar_observation_receipt_tenant_observation"),
    )
    op.create_index("ix_radar_observation_receipt_tenant_source_message", "radar_observation_receipt", ["tenant_id", "source_id", "message_id"])


def downgrade() -> None:
    op.drop_index("ix_radar_observation_receipt_tenant_source_message", table_name="radar_observation_receipt")
    op.drop_table("radar_observation_receipt")
