"""Add immutable content-campaign recipient snapshots.

Revision ID: 20260906_21
Revises: 20260901_20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260906_21"
down_revision = "20260901_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("broadcast_campaigns", sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("broadcast_campaigns", sa.Column("audience_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("broadcast_campaigns", sa.Column("audience_count_snapshot", sa.Integer(), nullable=True))
    op.add_column("broadcast_campaigns", sa.Column("excluded_count_snapshot", sa.Integer(), nullable=True))
    op.create_table(
        "campaign_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("outbox_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["broadcast_campaigns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["outbox_message_id"], ["outbound_messages.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_campaign_recipients_campaign_user"),
    )
    op.create_index("ix_campaign_recipients_campaign_state", "campaign_recipients", ["campaign_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_campaign_recipients_campaign_state", table_name="campaign_recipients")
    op.drop_table("campaign_recipients")
    op.drop_column("broadcast_campaigns", "excluded_count_snapshot")
    op.drop_column("broadcast_campaigns", "audience_count_snapshot")
    op.drop_column("broadcast_campaigns", "audience_snapshot_json")
    op.drop_column("broadcast_campaigns", "snapshot_at")
