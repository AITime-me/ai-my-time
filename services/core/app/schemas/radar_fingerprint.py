"""Canonical revision fingerprint for Radar Observation v1.

Algorithm (deterministic, not Python hash()):
1. Build a fingerprint object from immutable semantic revision fields only.
2. Serialize as UTF-8 JSON with sorted keys, no insignificant whitespace,
   and ``separators=(",", ":")``.
3. Represent datetimes as UTC with fixed form ``YYYY-MM-DDTHH:MM:SS.ffffffZ``.
4. Represent missing optional values as JSON ``null``.
5. Digest with SHA-256; hex-encode lowercase 64 characters.

Included for ``message_upsert``:
- connector, source_id, peer_type, peer_id, message_id
- event_kind
- published_at, edited_at
- content.kind, content.text

Included for ``message_deleted``:
- connector, source_id, peer_type, peer_id, message_id
- event_kind
- published_at (null if absent), edited_at
- content is always null in the fingerprint object

``peer_id`` in the fingerprint is the canonical unsigned raw entity id
(never a Telethon ``-100…`` marked form).

Excluded (transport / display / attempt metadata):
- observation_id, origin, detected_at
- author.*, links.*
- manifest_version, schema_version
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.radar_v1 import (
    RadarContentKind,
    RadarEventKind,
    RadarObservationV1,
)


class RadarFingerprintMismatchError(ValueError):
    """Reader-supplied revision_fingerprint does not match Core recomputation."""


def canonical_utc_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("fingerprint datetime must be timezone-aware")
    utc = value.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def fingerprint_payload(observation: RadarObservationV1) -> dict[str, Any]:
    content: dict[str, Any] | None
    if observation.event_kind is RadarEventKind.MESSAGE_DELETED:
        content = None
    else:
        assert observation.content is not None
        content = {
            "kind": observation.content.kind.value,
            "text": observation.content.text,
        }
        if observation.content.kind is RadarContentKind.EMPTY:
            content = {"kind": RadarContentKind.EMPTY.value, "text": None}

    return {
        "connector": observation.connector,
        "content": content,
        "edited_at": canonical_utc_timestamp(observation.edited_at),
        "event_kind": observation.event_kind.value,
        "message_id": observation.message_id,
        "peer_id": observation.peer_id,
        "peer_type": observation.peer_type.value,
        "published_at": canonical_utc_timestamp(observation.published_at),
        "source_id": observation.source_id,
    }


def compute_revision_fingerprint(observation: RadarObservationV1) -> str:
    payload = fingerprint_payload(observation)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assert_revision_fingerprint_matches(observation: RadarObservationV1) -> str:
    expected = compute_revision_fingerprint(observation)
    if observation.revision_fingerprint != expected:
        raise RadarFingerprintMismatchError(
            "revision_fingerprint does not match canonical Core computation"
        )
    return expected
