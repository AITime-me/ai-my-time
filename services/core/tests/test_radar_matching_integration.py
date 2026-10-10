"""PostgreSQL proof that ingress matching creates one durable tenant signal."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from app.db.session import create_session_factory, session_scope
from app.models import (
    RadarObservationReceipt,
    RadarAlertOutbox,
    RadarDestination,
    RadarProfileDestination,
    RadarProfileSource,
    RadarProfileVersion,
    RadarSearchProfile,
    RadarSearchRule,
    RadarSignal,
    RadarSource,
    RadarTenant,
)
from app.services.radar_matching import RadarMatchingService
from app.services.radar_alert_projection import RadarAlertProjectionService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_match_materializes_single_excluded_signal() -> None:
    asyncio.run(_run_match_materialization(_test_database_url()))


async def _run_match_materialization(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE radar_alert_outbox, radar_signal, radar_observation_receipt, radar_profile_source, "
                    "radar_search_rule, radar_profile_version, radar_search_profile, radar_source, "
                    "radar_reader, radar_tenant RESTART IDENTITY CASCADE"
                )
            )
            tenant = RadarTenant(slug="matching")
            session.add(tenant)
            await session.flush()
            # Reader identity is only relevant to ingress; source FK is enough
            # for this isolated matching proof.
            reader_id = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO radar_reader (id, tenant_id, reader_key, credential_key_id, enabled, "
                    "journal_backlog, created_at, updated_at) VALUES "
                    "(:id, :tenant_id, 'matching-reader', 'matching-credential', true, 0, now(), now())"
                ),
                {"id": reader_id, "tenant_id": tenant.id},
            )
            source = RadarSource(
                tenant_id=tenant.id,
                reader_id=reader_id,
                peer_type="channel",
                peer_id=42,
                source_type="channel",
                is_approved=True,
                monitoring_capability="realtime",
            )
            profile = RadarSearchProfile(tenant_id=tenant.id, name="CRM")
            session.add_all([source, profile])
            await session.flush()
            version = RadarProfileVersion(tenant_id=tenant.id, profile_id=profile.id, version=1)
            session.add(version)
            await session.flush()
            profile.active_version_id = version.id
            destination = RadarDestination(
                tenant_id=tenant.id,
                bot_binding_key="radar-test-bot",
                chat_id=123456,
                verification_state="verified",
            )
            session.add(destination)
            await session.flush()
            session.add_all(
                [
                    RadarProfileSource(
                        tenant_id=tenant.id, profile_version_id=version.id, source_id=source.id
                    ),
                    RadarSearchRule(
                        tenant_id=tenant.id,
                        profile_version_id=version.id,
                        rule_key="include-crm",
                        kind="include",
                        expression={"terms": ["crm"]},
                    ),
                    RadarProfileDestination(
                        tenant_id=tenant.id,
                        profile_version_id=version.id,
                        destination_id=destination.id,
                    ),
                    RadarSearchRule(
                        tenant_id=tenant.id,
                        profile_version_id=version.id,
                        rule_key="exclude-gambling",
                        kind="exclude",
                        expression={"terms": ["gambling"]},
                    ),
                ]
            )
            receipt = RadarObservationReceipt(
                tenant_id=tenant.id,
                reader_id=reader_id,
                source_id=source.id,
                observation_id=uuid.uuid4(),
                manifest_version="test",
                message_id="1",
                revision_fingerprint="a" * 64,
                payload_sha256="b" * 64,
                event_kind="message_upsert",
                origin="live",
                published_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                detected_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                payload={"content": {"kind": "text", "text": "CRM for gambling leads"}},
            )
            session.add(receipt)
            await session.flush()
            signal = await RadarMatchingService(session).materialize(receipt=receipt)
            assert signal.status == "excluded"
            assert signal.profile_version_id == version.id
            assert signal.matched_rule_keys == ["include-crm"]
            assert signal.excluded_rule_keys == ["exclude-gambling"]

            # Excluded signals never enter the Radar Bot outbox.
            assert await RadarAlertProjectionService(session).project(signal=signal, receipt=receipt) == 0

            matched_receipt = RadarObservationReceipt(
                tenant_id=tenant.id,
                reader_id=reader_id,
                source_id=source.id,
                observation_id=uuid.uuid4(),
                manifest_version="test",
                message_id="2",
                revision_fingerprint="c" * 64,
                payload_sha256="d" * 64,
                event_kind="message_upsert",
                origin="live",
                published_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                detected_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                payload={"content": {"kind": "text", "text": "Need CRM implementation"}},
            )
            session.add(matched_receipt)
            await session.flush()
            matched_signal = await RadarMatchingService(session).materialize(receipt=matched_receipt)
            assert matched_signal.status == "matched"
            projector = RadarAlertProjectionService(session)
            assert await projector.project(signal=matched_signal, receipt=matched_receipt) == 1
            assert await projector.project(signal=matched_signal, receipt=matched_receipt) == 0
            alerts = list(
                await session.scalars(
                    select(RadarAlertOutbox).where(RadarAlertOutbox.signal_id == matched_signal.id)
                )
            )
            assert len(alerts) == 1
            assert alerts[0].destination_id == destination.id
            assert alerts[0].status == "pending"
            assert alerts[0].payload["text"] == "Need CRM implementation"

            stored = (
                await session.scalars(
                    select(RadarSignal).where(
                        RadarSignal.tenant_id == tenant.id,
                        RadarSignal.observation_receipt_id == receipt.id,
                    )
                )
            ).all()
            assert len(stored) == 1
    finally:
        await factory.kw["bind"].dispose()
