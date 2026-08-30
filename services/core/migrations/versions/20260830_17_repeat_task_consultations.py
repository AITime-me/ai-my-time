"""Allow a repeat-task consultation to reference an existing diagnostic result.

Revision ID: 20260830_17
Revises: 20260830_16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260830_17"
down_revision = "20260830_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_consultation_requests_diagnostic_session", "consultation_requests", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT 1 FROM consultation_requests GROUP BY diagnostic_session_id HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicates is not None:
        raise RuntimeError("cannot safely restore diagnostic-session uniqueness while repeat-task requests exist")
    op.create_unique_constraint(
        "uq_consultation_requests_diagnostic_session",
        "consultation_requests",
        ["diagnostic_session_id"],
    )
