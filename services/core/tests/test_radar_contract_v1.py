"""Radar Reader–Core contract v1: schemas, fingerprint, fixtures (no network/DB)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.radar_assets import list_fixture_names, load_fixture, load_json_schema
from app.schemas.radar_fingerprint import (
    RadarFingerprintMismatchError,
    assert_revision_fingerprint_matches,
    compute_revision_fingerprint,
)
from app.schemas.radar_v1 import (
    MAX_OBSERVATION_BYTES,
    RadarAckStatus,
    RadarAuthorV1,
    RadarContentKind,
    RadarContentV1,
    RadarErrorCode,
    RadarErrorV1,
    RadarEventKind,
    RadarHeartbeatV1,
    RadarObservationAckV1,
    RadarObservationV1,
    RadarOrigin,
    RadarPeerType,
    RadarReaderManifestV1,
)
from app.schemas.radar_validation import (
    RadarPayloadTooLargeError,
    RadarUnsupportedSchemaVersionError,
    assert_observation_within_size_limit,
    parse_observation_payload,
    serialized_observation_bytes,
    validate_observation_contract,
)

FORBIDDEN_WIRE_FIELD_NAMES = (
    "access_hash",
    "api_hash",
    "api_id",
    "bot_token",
    "phone_number",
    "session_string",
    "tenant_id",
)


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _live() -> RadarObservationV1:
    return RadarObservationV1.model_validate(load_fixture("observation.live_upsert.json"))


def test_valid_manifest_v1_fixture() -> None:
    manifest = RadarReaderManifestV1.model_validate(load_fixture("manifest.valid.json"))
    assert manifest.schema_version == 1
    assert manifest.sources[0].connector == "telegram"
    assert manifest.sources[0].peer_id.isdecimal()


def test_valid_observation_v1_fixture() -> None:
    observation = validate_observation_contract(_live())
    assert observation.event_kind is RadarEventKind.MESSAGE_UPSERT
    assert observation.origin is RadarOrigin.LIVE


def test_schema_version_mismatch_and_unsupported() -> None:
    payload = load_fixture("observation.live_upsert.json")
    payload["schema_version"] = 2
    with pytest.raises(RadarUnsupportedSchemaVersionError):
        parse_observation_payload(payload)
    payload["schema_version"] = "1"
    with pytest.raises((ValidationError, RadarUnsupportedSchemaVersionError)):
        parse_observation_payload(payload)


def test_decimal_string_telegram_ids_accepted() -> None:
    observation = _live()
    assert observation.peer_id == "1001234567890"
    assert observation.message_id == "42"
    assert observation.author is not None
    assert observation.author.id == "8266714957"


def test_invalid_numeric_ids_rejected() -> None:
    payload = load_fixture("observation.live_upsert.json")
    payload["peer_id"] = "12.5"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)
    payload = load_fixture("observation.live_upsert.json")
    payload["message_id"] = "-42"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)
    payload = load_fixture("observation.live_upsert.json")
    payload["peer_id"] = "0123"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)


def test_timezone_aware_timestamps_required() -> None:
    payload = load_fixture("observation.live_upsert.json")
    payload["detected_at"] = "2026-10-10T08:00:00"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)


def test_nullable_author_and_links() -> None:
    observation = _live().model_copy(update={"author": None, "links": None})
    observation = observation.model_copy(
        update={"revision_fingerprint": compute_revision_fingerprint(observation)}
    )
    validate_observation_contract(observation)
    assert observation.author is None
    assert observation.links is None


def test_deletion_representation() -> None:
    deleted = RadarObservationV1.model_validate(load_fixture("observation.message_deleted.json"))
    validate_observation_contract(deleted)
    assert deleted.event_kind is RadarEventKind.MESSAGE_DELETED
    assert deleted.content is None
    assert deleted.author is None
    assert deleted.links is None
    assert deleted.published_at is None


def test_deterministic_fingerprint() -> None:
    first = compute_revision_fingerprint(_live())
    second = compute_revision_fingerprint(_live())
    assert first == second
    assert len(first) == 64


def test_live_and_catch_up_same_revision_same_fingerprint() -> None:
    live = RadarObservationV1.model_validate(load_fixture("observation.live_upsert.json"))
    catch = RadarObservationV1.model_validate(
        load_fixture("observation.catch_up_same_revision.json")
    )
    assert live.observation_id != catch.observation_id
    assert live.detected_at != catch.detected_at
    assert live.origin != catch.origin
    assert live.source_id == catch.source_id
    assert live.message_id == catch.message_id
    assert live.revision_fingerprint == catch.revision_fingerprint
    assert compute_revision_fingerprint(live) == compute_revision_fingerprint(catch)


def test_origin_observation_id_detected_at_do_not_change_fingerprint() -> None:
    base = _live()
    expected = compute_revision_fingerprint(base)
    variants = [
        base.model_copy(update={"origin": RadarOrigin.RECONCILIATION}),
        base.model_copy(update={"observation_id": UUID("99999999-9999-4999-8999-999999999999")}),
        base.model_copy(update={"detected_at": _ts("2026-10-10T12:00:00.000000Z")}),
    ]
    for variant in variants:
        assert compute_revision_fingerprint(variant) == expected


def test_content_edit_changes_fingerprint() -> None:
    live = _live()
    edited = RadarObservationV1.model_validate(load_fixture("observation.edit_upsert.json"))
    assert compute_revision_fingerprint(live) != compute_revision_fingerprint(edited)
    assert live.revision_fingerprint != edited.revision_fingerprint


def test_fingerprint_mismatch_rejected() -> None:
    observation = _live().model_copy(update={"revision_fingerprint": "a" * 64})
    with pytest.raises(RadarFingerprintMismatchError):
        assert_revision_fingerprint_matches(observation)
    with pytest.raises(RadarFingerprintMismatchError):
        validate_observation_contract(observation)


def test_forbidden_credential_fields_absent_from_dto_schema_and_fixtures() -> None:
    schemas = [
        RadarObservationV1.model_json_schema(),
        RadarReaderManifestV1.model_json_schema(),
        RadarHeartbeatV1.model_json_schema(),
        RadarObservationAckV1.model_json_schema(),
        RadarErrorV1.model_json_schema(),
    ]
    for schema in schemas:
        property_names = set(schema.get("properties", {}))
        for defs in schema.get("$defs", {}).values():
            property_names.update(defs.get("properties", {}))
        for token in FORBIDDEN_WIRE_FIELD_NAMES:
            assert token not in property_names

    for name in list_fixture_names():
        keys = set(load_fixture(name).keys())
        for token in FORBIDDEN_WIRE_FIELD_NAMES:
            assert token not in keys

    payload = load_fixture("observation.live_upsert.json")
    payload["access_hash"] = "secret"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)
    payload = load_fixture("observation.live_upsert.json")
    payload["tenant_id"] = "tenant-x"
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)


def test_ack_accepted_and_duplicate_semantics() -> None:
    accepted = RadarObservationAckV1.model_validate(load_fixture("ack.accepted.json"))
    duplicate = RadarObservationAckV1.model_validate(load_fixture("ack.duplicate.json"))
    assert accepted.status is RadarAckStatus.ACCEPTED
    assert duplicate.status is RadarAckStatus.DUPLICATE
    assert accepted.observation_id == duplicate.observation_id
    # accepted means durable receipt only — contract status enum has no delivery/signal states
    assert set(RadarAckStatus) == {RadarAckStatus.ACCEPTED, RadarAckStatus.DUPLICATE}


def test_safe_error_contract() -> None:
    error = RadarErrorV1.model_validate(load_fixture("error.idempotency_conflict.json"))
    assert error.code is RadarErrorCode.IDEMPOTENCY_CONFLICT
    assert error.http_status == 409
    assert "session" not in error.message.lower()
    assert error.retry_after_seconds is None


def test_oversized_serialized_observation_rejected() -> None:
    observation = _live()
    huge_text = "x" * (MAX_OBSERVATION_BYTES + 100)
    with pytest.raises(ValidationError):
        # field max_length should reject first
        RadarContentV1(kind=RadarContentKind.TEXT, text=huge_text)

    # Bypass content max_length by constructing oversized JSON bytes directly.
    payload = observation.model_dump(mode="json")
    payload["content"] = {"kind": "text", "text": "y" * (MAX_OBSERVATION_BYTES)}
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert len(raw) > MAX_OBSERVATION_BYTES
    with pytest.raises(RadarPayloadTooLargeError):
        parse_observation_payload(raw)


def test_observation_size_helper_accepts_valid_payload() -> None:
    size = assert_observation_within_size_limit(_live())
    assert 0 < size <= MAX_OBSERVATION_BYTES
    assert len(serialized_observation_bytes(_live())) == size


def test_json_schema_and_fixtures_validate() -> None:
    mapping = {
        "manifest.valid.json": ("manifest.schema.json", RadarReaderManifestV1),
        "observation.live_upsert.json": ("observation.schema.json", RadarObservationV1),
        "observation.catch_up_same_revision.json": ("observation.schema.json", RadarObservationV1),
        "observation.edit_upsert.json": ("observation.schema.json", RadarObservationV1),
        "observation.message_deleted.json": ("observation.schema.json", RadarObservationV1),
        "ack.accepted.json": ("ack.schema.json", RadarObservationAckV1),
        "ack.duplicate.json": ("ack.schema.json", RadarObservationAckV1),
        "error.idempotency_conflict.json": ("error.schema.json", RadarErrorV1),
        "heartbeat.valid.json": ("heartbeat.schema.json", RadarHeartbeatV1),
    }
    for fixture_name, (schema_name, model) in mapping.items():
        schema = load_json_schema(schema_name)
        assert schema.get("title") or schema.get("properties")
        model.model_validate(load_fixture(fixture_name))


def test_message_upsert_requires_published_at() -> None:
    payload = load_fixture("observation.live_upsert.json")
    payload["published_at"] = None
    with pytest.raises(ValidationError):
        RadarObservationV1.model_validate(payload)


def test_author_display_name_does_not_affect_fingerprint() -> None:
    base = _live()
    expected = compute_revision_fingerprint(base)
    changed = base.model_copy(
        update={
            "author": RadarAuthorV1(
                id="8266714957",
                username="other",
                display_name="Changed Display",
                author_type=base.author.author_type if base.author else None,
            )
        }
    )
    assert compute_revision_fingerprint(changed) == expected


def test_assets_package_lists_all_committed_fixtures() -> None:
    names = list_fixture_names()
    assert "observation.live_upsert.json" in names
    assert "observation.catch_up_same_revision.json" in names
    assets_dir = Path(__file__).resolve().parents[1] / "app" / "radar_assets" / "fixtures" / "v1"
    assert sorted(path.name for path in assets_dir.glob("*.json")) == names
