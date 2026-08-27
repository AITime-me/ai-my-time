"""Add bounded Diagnostic AI dialogue storage and role split.

Revision ID: 20260827_07
Revises: 20260826_06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260827_07"
down_revision = "20260826_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "diagnostic_reports",
        sa.Column("role_split_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.create_table(
        "diagnostic_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("diagnostic_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["diagnostic_session_id"], ["diagnostic_sessions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("diagnostic_session_id", "turn_index", name="uq_diagnostic_turns_session_index"),
    )
    op.create_index("ix_diagnostic_turns_session_index", "diagnostic_turns", ["diagnostic_session_id", "turn_index"])


def downgrade() -> None:
    op.drop_index("ix_diagnostic_turns_session_index", table_name="diagnostic_turns")
    op.drop_table("diagnostic_turns")
    op.drop_column("diagnostic_reports", "role_split_json")
