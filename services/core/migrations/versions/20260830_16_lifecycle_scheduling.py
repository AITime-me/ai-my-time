"""Add consultation lifecycle fields and durable scheduled events.

Revision ID: 20260830_16
Revises: 20260829_15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260830_16"
down_revision = "20260829_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE consultation_requests SET status = 'waiting_response' WHERE status = 'in_progress'")
    op.add_column("consultation_requests", sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consultation_requests", sa.Column("confirmation_state", sa.String(length=24), nullable=False, server_default="pending"))
    op.add_column("consultation_requests", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consultation_requests", sa.Column("confirmation_source", sa.String(length=24), nullable=True))
    op.add_column("consultation_requests", sa.Column("commercial_result", sa.String(length=24), nullable=True))
    op.add_column("consultation_requests", sa.Column("origin_type", sa.String(length=32), nullable=False, server_default="primary_diagnostic"))
    op.add_column("consultation_requests", sa.Column("repeat_task_text", sa.Text(), nullable=True))
    op.add_column("consultation_requests", sa.Column("reschedule_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "scheduled_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("consultation_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("consultation_requests.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("diagnostic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("diagnostic_sessions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("idempotency_key", name="uq_scheduled_events_idempotency_key"),
    )
    op.create_index("ix_scheduled_events_status_due", "scheduled_events", ["status", "due_at"])
    op.create_index("ix_scheduled_events_consultation_status", "scheduled_events", ["consultation_request_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_scheduled_events_consultation_status", table_name="scheduled_events")
    op.drop_index("ix_scheduled_events_status_due", table_name="scheduled_events")
    op.drop_table("scheduled_events")
    for column in ("reschedule_requested_at", "repeat_task_text", "origin_type", "commercial_result", "confirmation_source", "confirmed_at", "confirmation_state", "appointment_at"):
        op.drop_column("consultation_requests", column)
    op.execute("UPDATE consultation_requests SET status = 'in_progress' WHERE status = 'waiting_response'")
