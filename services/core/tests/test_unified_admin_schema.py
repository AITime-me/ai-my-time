"""Static contract coverage for the additive Unified Admin foundation."""

from app.models import (
    AssistantChannelBinding,
    AssistantConversation,
    AssistantMessage,
    AssistantProfile,
    AssistantProfileVersion,
    AssistantRun,
    ConsentRecord,
    IntakeRequest,
    SiteCase,
    SiteFaq,
    SiteLegalDocument,
    SiteLegalDocumentVersion,
    SiteService,
    SiteSettings,
)
from app.models.core import AttentionItem, ConsultationRequest


def test_unified_admin_additions_keep_assistant_separate_from_diagnostics() -> None:
    assert "diagnostic_session_id" not in AssistantConversation.__table__.c
    assert "diagnostic_session_id" not in AssistantMessage.__table__.c
    assert "diagnostic_session_id" not in AssistantRun.__table__.c
    assert AssistantConversation.__table__.c.user_id.nullable
    assert AssistantRun.__table__.c.profile_version_id.nullable is False


def test_intake_is_the_only_new_public_work_origin() -> None:
    consultation = ConsultationRequest.__table__
    assert consultation.c.diagnostic_session_id.nullable
    assert consultation.c.intake_request_id.nullable
    assert any(item.name == "ck_consultation_requests_origin" for item in consultation.constraints)
    assert any(item.name == "uq_consultation_requests_intake_request" for item in consultation.constraints)
    assert "intake_request_id" in AttentionItem.__table__.c
    assert IntakeRequest.__table__.c.user_id.nullable
    assert IntakeRequest.__table__.c.assistant_conversation_id.nullable
    assert "assistant_handoffs" not in IntakeRequest.metadata.tables


def test_content_consent_and_assistant_key_constraints_are_present() -> None:
    assert SiteSettings.__table__.c.id.primary_key
    assert any(item.name == "ck_site_settings_singleton" for item in SiteSettings.__table__.constraints)
    assert any(item.name == "uq_site_services_slug" for item in SiteService.__table__.constraints)
    assert SiteCase.__table__.c.legacy_source_id.unique
    assert SiteFaq.__table__.c.legacy_source_id.unique
    assert any(item.name == "uq_site_legal_documents_key" for item in SiteLegalDocument.__table__.constraints)
    assert any(item.name == "uq_site_legal_document_versions_document_version" for item in SiteLegalDocumentVersion.__table__.constraints)
    assert any(item.name == "uq_assistant_profiles_key" for item in AssistantProfile.__table__.constraints)
    assert any(item.name == "uq_assistant_profile_versions_profile_version" for item in AssistantProfileVersion.__table__.constraints)
    assert any(item.name == "uq_assistant_channel_bindings_channel" for item in AssistantChannelBinding.__table__.constraints)
    assert ConsentRecord.__table__.c.legal_document_version_id.nullable
