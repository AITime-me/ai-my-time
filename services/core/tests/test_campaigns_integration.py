"""PostgreSQL proof for immutable, subscription-safe content campaigns."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import AdminSegment, AdminUser, CampaignRecipient, OutboundMessage, User, UserIdentity
from app.services.admin_broadcasts import AdminCampaignService
from app.services.outbox_delivery import OutboundDeliveryService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_campaign_snapshot_and_stop_guard() -> None:
    asyncio.run(_run(_test_database_url()))


async def _run(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await _cleanup_campaign_test_data(session)
            owner = AdminUser(email="owner-campaign-test@example.invalid", password_hash="test", role="owner")
            subscribed = User(display_name="Subscribed", content_subscription_status="subscribed", communication_status="subscribed")
            stopped = User(display_name="Stopped", content_subscription_status="unsubscribed", communication_status="subscribed")
            session.add_all([owner, subscribed, stopped]); await session.flush()
            session.add_all([
                UserIdentity(user_id=subscribed.id, provider="telegram", connection_scope="lead", external_id="campaign-test-1"),
                UserIdentity(user_id=stopped.id, provider="telegram", connection_scope="lead", external_id="campaign-test-2"),
            ])
            audience = AdminSegment(key="campaign-test-audience", title="Campaign test", definition_json={}, is_active=True, is_system=False)
            session.add(audience); await session.flush()
            service = AdminCampaignService(session)
            draft = await service.create(actor_id=owner.id, segment_id=audience.id, title="Useful material", body="A useful, local-only test message.")
            assert draft is not None
            preview = await service.campaign(draft.id)
            assert preview is not None
            assert (preview.audience_count, preview.eligible_count, preview.excluded_count) == (2, 1, 1)
            confirmed = await service.confirm(actor_id=owner.id, campaign_id=draft.id)
            assert confirmed is not None
            assert confirmed.status == "queued"
            assert (confirmed.audience_count, confirmed.eligible_count, confirmed.excluded_count) == (2, 1, 1)
            assert confirmed.snapshot_at is not None
            assert await service.update(actor_id=owner.id, campaign_id=draft.id, segment_id=audience.id, title="changed", body="changed") is None
            assert not await service.delete(actor_id=owner.id, campaign_id=draft.id)
            assert (await session.scalar(select(CampaignRecipient).where(CampaignRecipient.campaign_id == draft.id))) is not None
            assert (await session.scalar(select(OutboundMessage).where(OutboundMessage.dedupe_key == f"campaign:{draft.id}:user:{subscribed.id}"))) is not None
            # The campaign has a durable recipient row and confirmation is idempotent.
            again = await service.confirm(actor_id=owner.id, campaign_id=draft.id)
            assert again is not None and again.eligible_count == 1
            subscribed.content_subscription_status = "unsubscribed"

        async with session_scope(factory) as session:
            deliveries = await OutboundDeliveryService(session).claim(limit=10)
            assert deliveries == []
            message = await session.scalar(select(OutboundMessage))
            recipient = await session.scalar(select(CampaignRecipient))
            user = await session.get(User, subscribed.id)
            assert message is not None and message.status == "skipped" and message.last_error_code == "content_unsubscribed"
            assert recipient is not None and recipient.state == "skipped"
            # /stop for content leaves unrelated communication consent alone.
            assert user is not None and user.communication_status == "subscribed"
    finally:
        try:
            async with session_scope(factory) as session:
                await _cleanup_campaign_test_data(session)
        finally:
            await factory.kw["bind"].dispose()


async def _cleanup_campaign_test_data(session) -> None:
    """Do not erase migration-owned system audiences from the shared test DB."""
    await session.execute(text("DELETE FROM campaign_recipients WHERE campaign_id IN (SELECT id FROM broadcast_campaigns WHERE title = 'Useful material')"))
    await session.execute(text("DELETE FROM outbound_messages WHERE dedupe_key LIKE 'campaign:%'"))
    await session.execute(text("DELETE FROM broadcast_campaigns WHERE title = 'Useful material'"))
    await session.execute(text("DELETE FROM admin_segments WHERE key = 'campaign-test-audience'"))
    await session.execute(text("DELETE FROM user_identities WHERE external_id IN ('campaign-test-1', 'campaign-test-2')"))
    await session.execute(text("DELETE FROM users WHERE display_name IN ('Subscribed', 'Stopped')"))
    await session.execute(text("DELETE FROM admin_audit_events WHERE actor_id IN (SELECT id FROM admin_users WHERE email = 'owner-campaign-test@example.invalid')"))
    await session.execute(text("DELETE FROM admin_users WHERE email = 'owner-campaign-test@example.invalid'"))
