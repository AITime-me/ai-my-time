"""Keep acceptance profile runs separate from historical LeadBotSession rows."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_11"
down_revision = "20260828_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_acceptance_flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=80), nullable=False, server_default="business_type"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("flow_version", sa.String(length=20), nullable=False, server_default="v2"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["grant_id"], ["diagnostic_acceptance_grants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("grant_id", name="uq_diagnostic_acceptance_flows_grant_id"),
    )
    op.create_index("ix_diagnostic_acceptance_flows_user_status", "diagnostic_acceptance_flows", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_diagnostic_acceptance_flows_user_status", table_name="diagnostic_acceptance_flows")
    op.drop_table("diagnostic_acceptance_flows")
