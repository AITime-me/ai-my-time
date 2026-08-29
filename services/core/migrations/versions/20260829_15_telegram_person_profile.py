"""Persist mutable Telegram Person profile fields.

Revision ID: 20260829_15
Revises: 20260828_14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260829_15"
down_revision = "20260828_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_first_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("telegram_last_name", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_last_name")
    op.drop_column("users", "telegram_first_name")
