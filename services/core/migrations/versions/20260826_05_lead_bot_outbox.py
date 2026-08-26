"""Add durable Lead Bot state and provider-neutral outbound queue.

Revision ID: 20260826_05
Revises: 20260826_04
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_05"
down_revision = "20260826_04"
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "lead_bot_sessions",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False, server_default="business_type"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "outbound_messages",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("dedupe_key", name="uq_outbound_messages_dedupe_key"),
    )
    op.create_index("ix_outbound_messages_status_created", "outbound_messages", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbound_messages_status_created", table_name="outbound_messages")
    op.drop_table("outbound_messages")
    op.drop_table("lead_bot_sessions")
