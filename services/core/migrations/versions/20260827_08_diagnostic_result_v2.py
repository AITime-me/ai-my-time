"""Store the versioned internal Diagnostic AI result without replacing v1."""

from alembic import op
import sqlalchemy as sa

revision = "20260827_08"
down_revision = "20260827_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("diagnostic_reports", sa.Column("result_version", sa.String(length=20), nullable=False, server_default="v1"))
    op.add_column("diagnostic_reports", sa.Column("result_json", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("diagnostic_reports", "result_json")
    op.drop_column("diagnostic_reports", "result_version")
