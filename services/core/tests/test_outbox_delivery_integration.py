"""PostgreSQL proof that outbound work is leased, idempotent and retryable."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import OutboundMessage
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.outbox import OutboundQueue
from app.services.outbox_delivery import OutboundDelivery, OutboundWorker


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


class RecordingTransport:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.sent: list[OutboundDelivery] = []
        self._fail_once = fail_once

    async def deliver(self, message: OutboundDelivery) -> None:
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("temporary test failure")
        self.sent.append(message)


def test_outbox_worker_leases_sends_and_retries() -> None:
    asyncio.run(_run_worker(_test_database_url()))


async def _run_worker(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE outbound_messages, user_identities, users RESTART IDENTITY CASCADE"))
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(telegram_user_id="900003", qr_code="qr_conf_main")
            )
            await OutboundQueue(session).enqueue(
                user_id=entry.user_id,
                channel="telegram_lead",
                payload={"kind": "message", "text": "local test", "buttons": []},
                dedupe_key="test:outbox:delivery",
            )
        transport = RecordingTransport(fail_once=True)
        worker = OutboundWorker(factory, transport)
        assert await worker.run_once() == 0
        assert await worker.run_once() == 1
        assert await worker.run_once() == 0
        assert len(transport.sent) == 1
        async with session_scope(factory) as session:
            row = await session.scalar(select(OutboundMessage))
            assert row is not None
            assert row.status == "sent"
            assert row.attempt_count == 2
            assert row.sent_at is not None
            assert row.lease_token is None
    finally:
        try:
            async with session_scope(factory) as session:
                await session.execute(text("TRUNCATE TABLE outbound_messages, user_identities, users RESTART IDENTITY CASCADE"))
        finally:
            await factory.kw["bind"].dispose()
