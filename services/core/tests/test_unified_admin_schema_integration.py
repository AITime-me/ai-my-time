"""PostgreSQL proof for the additive Website + Assistant relationship graph."""

from __future__ import annotations

import asyncio
import os

import pytest

from app.db.session import create_session_factory
from app.models import (
    AssistantConversation,
    AssistantMessage,
    AssistantProfile,
    AssistantProfileVersion,
    AssistantRun,
    ConsentRecord,
    IntakeRequest,
    SiteLegalDocument,
    SiteLegalDocumentVersion,
    SiteCase,
    SiteFaq,
    SiteService,
    User,
)
from app.models.core import AttentionItem, ConsultationRequest
from app.services.public_knowledge import PublicKnowledgeReader


def _database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_assistant_intake_can_create_consultation_without_diagnostic() -> None:
    asyncio.run(_run(_database_url()))


async def _run(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with factory() as session:
            transaction = await session.begin()
            try:
                user = User(display_name="Unified schema test")
                document = SiteLegalDocument(key="schema-test", title="Schema test")
                profile = AssistantProfile(key="schema-test", title="Schema test assistant")
                session.add_all([user, document, profile])
                session.add_all([
                    SiteService(slug="schema-test-service", title="Schema test service", is_active=True),
                    SiteCase(title="Schema test case", is_active=True),
                    SiteFaq(question="Schema test question?", answer="Schema test answer.", is_active=True),
                ])
                await session.flush()

                legal_version = SiteLegalDocumentVersion(
                    document_id=document.id,
                    version=1,
                    status="published",
                    content="Test-only legal content.",
                )
                profile_version = AssistantProfileVersion(
                    profile_id=profile.id,
                    version=1,
                    status="published",
                    config_json={"knowledge_namespace": "site_assistant"},
                )
                session.add_all([legal_version, profile_version])
                await session.flush()

                conversation = AssistantConversation(
                    user_id=user.id,
                    channel="web",
                    session_key_hash="a" * 64,
                )
                consent = ConsentRecord(
                    user_id=user.id,
                    purpose="intake",
                    decision="granted",
                    legal_document_version_id=legal_version.id,
                    channel="web",
                )
                session.add_all([conversation, consent])
                await session.flush()

                message = AssistantMessage(
                    conversation_id=conversation.id,
                    actor="visitor",
                    content="Нужна консультация.",
                )
                intake = IntakeRequest(
                    user_id=user.id,
                    assistant_conversation_id=conversation.id,
                    consent_record_id=consent.id,
                    channel="web_assistant",
                    kind="consultation",
                    dedupe_key="schema-test-intake",
                )
                session.add_all([message, intake])
                await session.flush()

                run = AssistantRun(
                    conversation_id=conversation.id,
                    input_message_id=message.id,
                    profile_version_id=profile_version.id,
                    status="completed",
                    outcome="handoff_requested",
                )
                consultation = ConsultationRequest(
                    user_id=user.id,
                    diagnostic_session_id=None,
                    intake_request_id=intake.id,
                    origin_type="web_assistant",
                )
                attention = AttentionItem(
                    user_id=user.id,
                    intake_request_id=intake.id,
                    kind="intake_review",
                    reason="Test-only handoff trace.",
                )
                session.add_all([run, consultation, attention])
                await session.flush()

                assert consultation.diagnostic_session_id is None
                assert consultation.intake_request_id == intake.id
                assert attention.intake_request_id == intake.id
                assert run.profile_version_id == profile_version.id
                public_knowledge = await PublicKnowledgeReader(session).snapshot()
                assert [item["slug"] for item in public_knowledge["services"]] == ["schema-test-service"]
                assert [item["title"] for item in public_knowledge["cases"]] == ["Schema test case"]
                assert [item["question"] for item in public_knowledge["faq"]] == ["Schema test question?"]
            finally:
                await transaction.rollback()
    finally:
        await factory.kw["bind"].dispose()
