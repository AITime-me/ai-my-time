"""Add reproducible diagnostic session and result records.

Revision ID: 20260826_03
Revises: 20260826_02
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_03"
down_revision = "20260826_02"
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "diagnostic_sessions",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="prepared"),
        sa.Column("input_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_diagnostic_sessions_user_created", "diagnostic_sessions", ["user_id", "created_at"])
    op.create_table(
        "diagnostic_reports",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("diagnostic_session_id", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priorities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("next_steps_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("limitations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["diagnostic_session_id"], ["diagnostic_sessions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("diagnostic_session_id", name="uq_diagnostic_reports_session"),
    )


def downgrade() -> None:
    op.drop_table("diagnostic_reports")
    op.drop_index("ix_diagnostic_sessions_user_created", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")
