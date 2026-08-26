"""Add profile answer history for Diagnostic AI input.

Revision ID: 20260826_02
Revises: 20260826_01
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_02"
down_revision = "20260826_01"
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "business_profiles",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="in_progress"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "profile_answers",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        sa.Column("question_code", sa.String(length=80), nullable=False),
        sa.Column("answer_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "question_code", "revision", name="uq_profile_answers_revision"),
    )
    op.create_index("ix_profile_answers_user_question", "profile_answers", ["user_id", "question_code"])


def downgrade() -> None:
    op.drop_index("ix_profile_answers_user_question", table_name="profile_answers")
    op.drop_table("profile_answers")
    op.drop_table("business_profiles")
