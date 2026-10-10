"""Pure contract tests for the Radar Bot outbox projection payload."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models import RadarObservationReceipt, RadarSignal
from app.services.radar_alert_projection import _alert_payload


def test_alert_payload_is_provider_neutral_and_carries_freshness() -> None:
    tenant_id = uuid.uuid4()
    signal = RadarSignal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        observation_receipt_id=uuid.uuid4(),
        status="matched",
        matched_rule_keys=["include-crm"],
        freshness_expires_at=datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc),
    )
    receipt = RadarObservationReceipt(
        tenant_id=tenant_id,
        reader_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        manifest_version="v1",
        message_id="42",
        revision_fingerprint="a" * 64,
        payload_sha256="b" * 64,
        event_kind="message_upsert",
        origin="live",
        detected_at=datetime(2026, 10, 10, 13, 0, tzinfo=timezone.utc),
        payload={"content": {"kind": "text", "text": "Need CRM implementation"}},
    )

    payload = _alert_payload(signal=signal, receipt=receipt)

    assert payload == {
        "kind": "radar_signal",
        "signal_id": str(signal.id),
        "observation_id": str(receipt.observation_id),
        "source_id": str(receipt.source_id),
        "source_label": str(receipt.source_id),
        "message_id": "42",
        "message_url": None,
        "text": "Need CRM implementation",
        "published_at": None,
        "detected_at": "2026-10-10T13:00:00+00:00",
        "freshness_expires_at": "2026-10-10T14:00:00+00:00",
        "profile_name": None,
        "matched_rule_keys": ["include-crm"],
        "reason": "совпали правила: include-crm",
    }
