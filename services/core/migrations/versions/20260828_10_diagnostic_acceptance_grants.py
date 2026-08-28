"""Add closed, one-use Diagnostic AI acceptance grants."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_10"
down_revision = "20260828_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_acceptance_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prior_flow_snapshot_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("token_hash", name="uq_diagnostic_acceptance_grants_token_hash"),
    )
    op.create_index(
        "ix_diagnostic_acceptance_grants_user_expires",
        "diagnostic_acceptance_grants",
        ["user_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_diagnostic_acceptance_grants_user_expires", table_name="diagnostic_acceptance_grants")
    op.drop_table("diagnostic_acceptance_grants")
