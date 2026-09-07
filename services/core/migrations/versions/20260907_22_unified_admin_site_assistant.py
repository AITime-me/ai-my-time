"""Add Unified Admin website and Assistant data foundations.

Revision ID: 20260907_22
Revises: 20260906_21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260907_22"
down_revision = "20260906_21"
branch_labels = None
depends_on = None


def _uuid(name: str, **kwargs: object) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("site_title", sa.String(length=256), nullable=False),
        sa.Column("site_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("og_image", sa.String(length=1024), nullable=True),
        sa.Column("contacts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("social_links_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("analytics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("id = 1", name="ck_site_settings_singleton"),
    )
    op.create_table(
        "site_services",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("h1", sa.String(length=256), nullable=True),
        sa.Column("seo_title", sa.String(length=256), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("full_description", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("includes", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.String(length=160), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _uuid("legacy_source_id", nullable=True, unique=True),
        *_timestamps(),
        sa.UniqueConstraint("slug", name="uq_site_services_slug"),
    )
    op.create_index("ix_site_services_public_order", "site_services", ["is_active", "sort_order"])
    op.create_table(
        "site_cases",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("task", sa.Text(), nullable=True),
        sa.Column("solution", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("seo_title", sa.String(length=256), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _uuid("legacy_source_id", nullable=True, unique=True),
        *_timestamps(),
    )
    op.create_index("ix_site_cases_public_order", "site_cases", ["is_active", "sort_order"])
    op.create_table(
        "site_faq",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _uuid("legacy_source_id", nullable=True, unique=True),
        *_timestamps(),
    )
    op.create_index("ix_site_faq_public_order", "site_faq", ["is_active", "sort_order"])
    op.create_table(
        "site_legal_documents",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        _uuid("published_version_id", nullable=True),
        _uuid("legacy_source_id", nullable=True, unique=True),
        *_timestamps(),
        sa.UniqueConstraint("key", name="uq_site_legal_documents_key"),
    )
    op.create_table(
        "site_legal_document_versions",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("document_id", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("content", sa.Text(), nullable=False),
        _uuid("created_by_actor_id", nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["site_legal_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_actor_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("document_id", "version", name="uq_site_legal_document_versions_document_version"),
    )
    op.create_index("ix_site_legal_document_versions_document_status", "site_legal_document_versions", ["document_id", "status", "created_at"])

    op.create_table(
        "assistant_profiles",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        _uuid("published_version_id", nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("key", name="uq_assistant_profiles_key"),
    )
    op.create_table(
        "assistant_profile_versions",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("profile_id", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        _uuid("created_by_actor_id", nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["profile_id"], ["assistant_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_actor_id"], ["admin_users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("profile_id", "version", name="uq_assistant_profile_versions_profile_version"),
    )
    op.create_index("ix_assistant_profile_versions_profile_status", "assistant_profile_versions", ["profile_id", "status", "created_at"])
    op.create_table(
        "assistant_channel_bindings",
        _uuid("id", primary_key=True, nullable=False),
        sa.Column("channel", sa.String(length=48), nullable=False),
        _uuid("profile_id", nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
        sa.ForeignKeyConstraint(["profile_id"], ["assistant_profiles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("channel", name="uq_assistant_channel_bindings_channel"),
    )
    op.create_table(
        "assistant_conversations",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("user_id", nullable=True),
        sa.Column("channel", sa.String(length=48), nullable=False),
        sa.Column("session_key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("attribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("channel", "session_key_hash", name="uq_assistant_conversations_channel_session"),
    )
    op.create_index("ix_assistant_conversations_user_activity", "assistant_conversations", ["user_id", "last_activity_at"])
    op.create_table(
        "assistant_messages",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("conversation_id", nullable=False),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_assistant_messages_conversation_created", "assistant_messages", ["conversation_id", "created_at"])
    op.create_table(
        "assistant_runs",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("conversation_id", nullable=False),
        _uuid("input_message_id", nullable=True),
        _uuid("profile_version_id", nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="started"),
        sa.Column("outcome", sa.String(length=80), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("knowledge_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["input_message_id"], ["assistant_messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_version_id"], ["assistant_profile_versions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_assistant_runs_conversation_created", "assistant_runs", ["conversation_id", "created_at"])
    op.create_index("ix_assistant_runs_status_created", "assistant_runs", ["status", "created_at"])

    op.create_table(
        "consent_records",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("user_id", nullable=True),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        _uuid("legal_document_version_id", nullable=True),
        sa.Column("channel", sa.String(length=48), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["legal_document_version_id"], ["site_legal_document_versions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_consent_records_user_purpose_captured", "consent_records", ["user_id", "purpose", "captured_at"])
    op.create_table(
        "intake_requests",
        _uuid("id", primary_key=True, nullable=False),
        _uuid("user_id", nullable=True),
        _uuid("assistant_conversation_id", nullable=True),
        _uuid("consent_record_id", nullable=True),
        sa.Column("channel", sa.String(length=48), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="new"),
        sa.Column("summary", sa.String(length=512), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dedupe_key", sa.String(length=180), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assistant_conversation_id"], ["assistant_conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["consent_record_id"], ["consent_records.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("dedupe_key", name="uq_intake_requests_dedupe_key"),
    )
    op.create_index("ix_intake_requests_state_created", "intake_requests", ["state", "created_at"])
    op.create_index("ix_intake_requests_user_created", "intake_requests", ["user_id", "created_at"])

    op.add_column("consultation_requests", _uuid("intake_request_id", nullable=True))
    op.alter_column("consultation_requests", "diagnostic_session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.create_foreign_key("fk_consultation_requests_intake_request", "consultation_requests", "intake_requests", ["intake_request_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_consultation_requests_intake_request", "consultation_requests", ["intake_request_id"])
    op.create_check_constraint("ck_consultation_requests_origin", "consultation_requests", "diagnostic_session_id IS NOT NULL OR intake_request_id IS NOT NULL")
    op.add_column("attention_items", _uuid("intake_request_id", nullable=True))
    op.create_foreign_key("fk_attention_items_intake_request", "attention_items", "intake_requests", ["intake_request_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_attention_items_intake_request", "attention_items", ["intake_request_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM consultation_requests WHERE diagnostic_session_id IS NULL)")).scalar():
        raise RuntimeError("cannot downgrade while intake-origin consultation requests exist")
    op.drop_index("ix_attention_items_intake_request", table_name="attention_items")
    op.drop_constraint("fk_attention_items_intake_request", "attention_items", type_="foreignkey")
    op.drop_column("attention_items", "intake_request_id")
    op.drop_constraint("ck_consultation_requests_origin", "consultation_requests", type_="check")
    op.drop_constraint("uq_consultation_requests_intake_request", "consultation_requests", type_="unique")
    op.drop_constraint("fk_consultation_requests_intake_request", "consultation_requests", type_="foreignkey")
    op.alter_column("consultation_requests", "diagnostic_session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_column("consultation_requests", "intake_request_id")
    for index, table in (
        ("ix_intake_requests_user_created", "intake_requests"),
        ("ix_intake_requests_state_created", "intake_requests"),
        ("ix_consent_records_user_purpose_captured", "consent_records"),
        ("ix_assistant_runs_status_created", "assistant_runs"),
        ("ix_assistant_runs_conversation_created", "assistant_runs"),
        ("ix_assistant_messages_conversation_created", "assistant_messages"),
        ("ix_assistant_conversations_user_activity", "assistant_conversations"),
        ("ix_assistant_profile_versions_profile_status", "assistant_profile_versions"),
        ("ix_site_legal_document_versions_document_status", "site_legal_document_versions"),
        ("ix_site_faq_public_order", "site_faq"),
        ("ix_site_cases_public_order", "site_cases"),
        ("ix_site_services_public_order", "site_services"),
    ):
        op.drop_index(index, table_name=table)
    for table in (
        "intake_requests", "consent_records", "assistant_runs", "assistant_messages",
        "assistant_conversations", "assistant_channel_bindings", "assistant_profile_versions",
        "assistant_profiles", "site_legal_document_versions", "site_legal_documents", "site_faq",
        "site_cases", "site_services", "site_settings",
    ):
        op.drop_table(table)
