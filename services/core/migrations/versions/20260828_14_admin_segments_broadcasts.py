"""Add bounded Admin segments and non-sending broadcast drafts.

Revision ID: 20260828_14
Revises: 20260828_13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_14"
down_revision = "20260828_13"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.add_column("users", sa.Column("marketing_consent_status", sa.String(length=24), nullable=False, server_default="unknown"))
    op.create_index("ix_users_broadcast_eligibility", "users", ["marketing_consent_status", "telegram_reachability", "communication_status"])
    op.create_table("admin_segments", _uuid("id", primary_key=True, nullable=False), sa.Column("key", sa.String(length=80), nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("definition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("key", name="uq_admin_segments_key"))
    op.create_table("broadcast_campaigns", _uuid("id", primary_key=True, nullable=False), _uuid("segment_id", nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"), _uuid("created_by_actor_id", nullable=False), sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["segment_id"], ["admin_segments.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["created_by_actor_id"], ["admin_users.id"], ondelete="RESTRICT"))
    op.create_index("ix_broadcast_campaigns_status_created", "broadcast_campaigns", ["status", "created_at"])
    op.execute("INSERT INTO admin_segments (id, key, title, definition_json) VALUES (gen_random_uuid(), 'eligible_telegram_broadcast', 'Telegram: подтверждённый допуск', '{\"marketing_consent\": \"confirmed\", \"reachability\": \"allowed\"}'::jsonb)")
    op.execute("INSERT INTO admin_segments (id, key, title, definition_json) VALUES (gen_random_uuid(), 'diagnostic_completed', 'Завершившие диагностику', '{\"diagnostic_completed\": true}'::jsonb)")


def downgrade() -> None:
    op.drop_index("ix_broadcast_campaigns_status_created", table_name="broadcast_campaigns")
    op.drop_table("broadcast_campaigns")
    op.drop_table("admin_segments")
    op.drop_index("ix_users_broadcast_eligibility", table_name="users")
    op.drop_column("users", "marketing_consent_status")
