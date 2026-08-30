"""Allow a lifecycle stage to retain a repeat-task diagnostic UUID.

Revision ID: 20260830_18
Revises: 20260830_17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260830_18"
down_revision = "20260830_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "lifecycle_stage",
        existing_type=sa.String(length=40),
        type_=sa.String(length=80),
        existing_nullable=False,
        existing_server_default=sa.text("'new'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    too_long = bind.execute(
        sa.text("SELECT 1 FROM users WHERE char_length(lifecycle_stage) > 40 LIMIT 1")
    ).first()
    if too_long is not None:
        raise RuntimeError("cannot safely shrink lifecycle_stage while repeat-task state is present")
    op.alter_column(
        "users",
        "lifecycle_stage",
        existing_type=sa.String(length=80),
        type_=sa.String(length=40),
        existing_nullable=False,
        existing_server_default=sa.text("'new'"),
    )
