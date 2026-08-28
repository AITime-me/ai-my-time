"""Add versioned business knowledge for the Admin control plane.

Revision ID: 20260828_13
Revises: 20260828_12
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_13"
down_revision = "20260828_12"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.create_table(
        "knowledge_assets",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        _uuid("published_version_id", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("namespace", "key", name="uq_knowledge_assets_namespace_key"),
    )
    op.create_table(
        "knowledge_versions",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("asset_id", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("comment", sa.String(length=512), nullable=True),
        _uuid("created_by_actor_id", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["asset_id"], ["knowledge_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_actor_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("asset_id", "version", name="uq_knowledge_versions_asset_version"),
    )
    op.create_index("ix_knowledge_versions_asset_status", "knowledge_versions", ["asset_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_versions_asset_status", table_name="knowledge_versions")
    op.drop_table("knowledge_versions")
    op.drop_table("knowledge_assets")
