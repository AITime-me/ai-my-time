"""Add a dedicated durable outbox for Radar Bot alerts.

Revision ID: 20261010_26
Revises: 20261010_25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261010_26"
down_revision = "20261010_25"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_unique_constraint("uq_radar_signal_tenant_id", "radar_signal", ["tenant_id", "id"])
    op.create_table(
        "radar_alert_outbox",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("tenant_id", nullable=False),
        _uuid("signal_id", nullable=False),
        _uuid("destination_id", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        _uuid("lease_token", nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["radar_tenant.id"], name="fk_radar_alert_outbox_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "signal_id"], ["radar_signal.tenant_id", "radar_signal.id"], name="fk_radar_alert_outbox_signal", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "destination_id"], ["radar_destination.tenant_id", "radar_destination.id"], name="fk_radar_alert_outbox_destination", ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "signal_id", "destination_id", name="uq_radar_alert_outbox_signal_destination"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'sent', 'failed', 'skipped')", name="ck_radar_alert_outbox_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_radar_alert_outbox_attempt_count"),
    )
    op.create_index("ix_radar_alert_outbox_status_created", "radar_alert_outbox", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_radar_alert_outbox_status_created", table_name="radar_alert_outbox")
    op.drop_table("radar_alert_outbox")
    op.drop_constraint("uq_radar_signal_tenant_id", "radar_signal", type_="unique")
