"""Add radar_source.config_version for Admin CAS.

Revision ID: 20261010_23
Revises: 20261010_22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261010_23"
down_revision = "20261010_22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "radar_source",
        sa.Column("config_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_check_constraint(
        "ck_radar_source_config_version",
        "radar_source",
        "config_version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_radar_source_config_version", "radar_source", type_="check")
    op.drop_column("radar_source", "config_version")
