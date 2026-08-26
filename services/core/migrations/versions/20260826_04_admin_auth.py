"""Add standalone Admin operator/session boundary.

Revision ID: 20260826_04
Revises: 20260826_03
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_04"
down_revision = "20260826_03"
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "admin_users",
        _uuid_column("id", primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "admin_sessions",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("admin_user_id", nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_sessions_user_expires", "admin_sessions", ["admin_user_id", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_sessions_user_expires", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_table("admin_users")
