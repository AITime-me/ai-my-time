"""Mark pre-v2 profile flows without changing their diagnostic snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "20260828_09"
down_revision = "20260827_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows are the historical lead flows. Their related DiagnosticSession
    # records are deliberately untouched.
    op.add_column(
        "lead_bot_sessions",
        sa.Column("flow_version", sa.String(length=20), nullable=False, server_default="legacy"),
    )
    # Rows created by the corrected application are v2 by default.
    op.alter_column("lead_bot_sessions", "flow_version", server_default="v2")


def downgrade() -> None:
    op.drop_column("lead_bot_sessions", "flow_version")
