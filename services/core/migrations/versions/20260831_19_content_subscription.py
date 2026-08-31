"""Store an explicit useful-materials subscription separately from lifecycle."""

from alembic import op
import sqlalchemy as sa


revision = "20260831_19"
down_revision = "20260830_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("content_subscription_status", sa.String(length=24), nullable=False, server_default="unsubscribed"),
    )


def downgrade() -> None:
    op.drop_column("users", "content_subscription_status")
