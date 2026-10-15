"""Add versioned Lead Bot runs and diagnostic-independent consultations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20261015_27"
down_revision = "20261010_26"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '60s'")
    op.create_table("lead_flow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("copy_version", sa.String(24), nullable=False, server_default="dual_v1"),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="open"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_json", JSONB(), nullable=False),
        sa.Column("answers_json", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_lead_flow_runs_user_created", "lead_flow_runs", ["user_id", "created_at"])
    op.create_table("lead_flow_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("interaction_id", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "interaction_id", name="uq_lead_flow_action_interaction"))
    op.add_column("consultation_requests", sa.Column("flow_run_id", UUID(as_uuid=True), nullable=True))
    op.add_column("consultation_requests", sa.Column("intake_snapshot_json", JSONB(), nullable=True))
    op.create_foreign_key("fk_consultation_flow_run", "consultation_requests", "lead_flow_runs", ["flow_run_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_consultation_flow_run", "consultation_requests", ["flow_run_id"])
    op.alter_column("consultation_requests", "diagnostic_session_id", nullable=True)
    op.create_check_constraint("ck_consultation_context", "consultation_requests", "diagnostic_session_id IS NOT NULL OR (flow_run_id IS NOT NULL AND origin_type IN ('ai_assistant_intro', 'business_intake'))")


def downgrade():
    # Refuse a destructive rollback once the new feature has durable data.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS(SELECT 1 FROM lead_flow_runs) OR EXISTS(SELECT 1 FROM lead_flow_actions)")).scalar():
        raise RuntimeError("New intake data exists; roll back via feature flag, retain schema")
    op.drop_constraint("ck_consultation_context", "consultation_requests", type_="check")
    op.alter_column("consultation_requests", "diagnostic_session_id", nullable=False)
    op.drop_constraint("uq_consultation_flow_run", "consultation_requests", type_="unique")
    op.drop_constraint("fk_consultation_flow_run", "consultation_requests", type_="foreignkey")
    op.drop_column("consultation_requests", "intake_snapshot_json")
    op.drop_column("consultation_requests", "flow_run_id")
    op.drop_table("lead_flow_actions")
    op.drop_table("lead_flow_runs")
