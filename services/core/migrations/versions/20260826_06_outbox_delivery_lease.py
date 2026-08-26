"""Add leases and retry metadata to the local outbound worker queue.

Revision ID: 20260826_06
Revises: 20260826_05
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_06"
down_revision = "20260826_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbound_messages",
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "outbound_messages",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbound_messages",
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outbound_messages", "last_error_code")
    op.drop_column("outbound_messages", "lease_expires_at")
    op.drop_column("outbound_messages", "lease_token")
