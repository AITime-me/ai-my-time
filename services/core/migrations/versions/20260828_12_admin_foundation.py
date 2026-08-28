"""Add Admin foundation entities without rewriting historical lead data.

Revision ID: 20260828_12
Revises: 20260828_11
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_12"
down_revision = "20260828_11"
branch_labels = None
depends_on = None


def _uuid_column(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=256), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("communication_status", sa.String(length=24), nullable=False, server_default="subscribed"),
    )
    op.add_column(
        "users",
        sa.Column("telegram_reachability", sa.String(length=24), nullable=False, server_default="unknown"),
    )
    op.create_index("ix_users_last_activity", "users", ["last_activity_at"])
    op.create_index(
        "ix_users_communication_reachability",
        "users",
        ["communication_status", "telegram_reachability"],
    )

    op.create_table(
        "consultation_requests",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        _uuid_column("diagnostic_session_id", nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["diagnostic_session_id"], ["diagnostic_sessions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("diagnostic_session_id", name="uq_consultation_requests_diagnostic_session"),
    )
    op.create_index("ix_consultation_requests_status_created", "consultation_requests", ["status", "created_at"])
    op.create_index("ix_consultation_requests_user_created", "consultation_requests", ["user_id", "created_at"])

    op.create_table(
        "attention_items",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("user_id", nullable=False),
        _uuid_column("consultation_request_id", nullable=True),
        _uuid_column("diagnostic_session_id", nullable=True),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=320), nullable=False),
        sa.Column("priority", sa.String(length=24), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="new"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["consultation_request_id"], ["consultation_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["diagnostic_session_id"], ["diagnostic_sessions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("consultation_request_id", name="uq_attention_items_consultation_request"),
    )
    op.create_index(
        "ix_attention_items_status_priority_created",
        "attention_items",
        ["status", "priority", "created_at"],
    )
    op.create_index("ix_attention_items_user_status", "attention_items", ["user_id", "status"])

    op.create_table(
        "admin_audit_events",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("actor_id", nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        _uuid_column("object_id", nullable=True),
        sa.Column("delta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["actor_id"], ["admin_users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_admin_audit_events_actor_created", "admin_audit_events", ["actor_id", "created_at"])
    op.create_index("ix_admin_audit_events_object_created", "admin_audit_events", ["object_type", "object_id", "created_at"])

    op.create_table(
        "operational_log_events",
        _uuid_column("id", primary_key=True, nullable=False),
        _uuid_column("trace_id", nullable=False),
        _uuid_column("user_id", nullable=True),
        _uuid_column("diagnostic_session_id", nullable=True),
        _uuid_column("outbox_message_id", nullable=True),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["diagnostic_session_id"], ["diagnostic_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["outbox_message_id"], ["outbound_messages.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_operational_log_events_created", "operational_log_events", ["created_at"])
    op.create_index("ix_operational_log_events_trace", "operational_log_events", ["trace_id", "created_at"])
    op.create_index("ix_operational_log_events_user_created", "operational_log_events", ["user_id", "created_at"])
    op.create_index(
        "ix_operational_log_events_component_status",
        "operational_log_events",
        ["component", "status", "created_at"],
    )

    op.execute(
        """
        INSERT INTO consultation_requests (id, user_id, diagnostic_session_id, status, created_at, updated_at)
        SELECT gen_random_uuid(), event.user_id, diagnostic.id, 'new', event.occurred_at, event.occurred_at
        FROM events AS event
        JOIN diagnostic_sessions AS diagnostic
          ON diagnostic.id = (event.payload_json ->> 'diagnostic_session_id')::uuid
         AND diagnostic.user_id = event.user_id
        WHERE event.kind = 'consultation_requested'
          AND event.payload_json ? 'diagnostic_session_id'
        ON CONFLICT (diagnostic_session_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO attention_items (
            id, user_id, consultation_request_id, diagnostic_session_id,
            kind, reason, priority, status, created_at, updated_at
        )
        SELECT gen_random_uuid(), request.user_id, request.id, request.diagnostic_session_id,
               'consultation_requested', 'Пользователь запросил онлайн-консультацию', 'normal', 'new',
               request.created_at, request.updated_at
        FROM consultation_requests AS request
        ON CONFLICT (consultation_request_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE users AS person
        SET last_activity_at = GREATEST(
            person.created_at,
            COALESCE((SELECT max(touchpoint.observed_at) FROM touchpoints AS touchpoint WHERE touchpoint.user_id = person.id), person.created_at),
            COALESCE((SELECT max(event.occurred_at) FROM events AS event WHERE event.user_id = person.id), person.created_at)
        )
        WHERE person.last_activity_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_operational_log_events_component_status", table_name="operational_log_events")
    op.drop_index("ix_operational_log_events_user_created", table_name="operational_log_events")
    op.drop_index("ix_operational_log_events_trace", table_name="operational_log_events")
    op.drop_index("ix_operational_log_events_created", table_name="operational_log_events")
    op.drop_table("operational_log_events")
    op.drop_index("ix_admin_audit_events_object_created", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_actor_created", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
    op.drop_index("ix_attention_items_user_status", table_name="attention_items")
    op.drop_index("ix_attention_items_status_priority_created", table_name="attention_items")
    op.drop_table("attention_items")
    op.drop_index("ix_consultation_requests_user_created", table_name="consultation_requests")
    op.drop_index("ix_consultation_requests_status_created", table_name="consultation_requests")
    op.drop_table("consultation_requests")
    op.drop_index("ix_users_communication_reachability", table_name="users")
    op.drop_index("ix_users_last_activity", table_name="users")
    op.drop_column("users", "telegram_reachability")
    op.drop_column("users", "communication_status")
    op.drop_column("users", "last_activity_at")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "display_name")
