"""Promote bounded Admin segments into dynamic audiences.

Revision ID: 20260901_20
Revises: 20260831_19
"""
from alembic import op
import sqlalchemy as sa

revision = "20260901_20"
down_revision = "20260831_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("admin_segments", sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.execute("UPDATE admin_segments SET is_active = false WHERE key IN ('eligible_telegram_broadcast', 'diagnostic_completed')")
    op.execute("INSERT INTO admin_segments (id, key, title, definition_json, is_active, is_system) VALUES (gen_random_uuid(), 'all_content_subscribers', 'Все подписанные на полезные материалы', '{\"content_subscription_status\": \"subscribed\"}'::jsonb, true, true) ON CONFLICT (key) DO UPDATE SET title = EXCLUDED.title, definition_json = EXCLUDED.definition_json, is_active = true, is_system = true")


def downgrade() -> None:
    op.execute("DELETE FROM admin_segments WHERE key = 'all_content_subscribers'")
    op.execute("UPDATE admin_segments SET is_active = true WHERE key IN ('eligible_telegram_broadcast', 'diagnostic_completed')")
    op.drop_column("admin_segments", "is_system")
