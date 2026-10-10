"""Contract-level helpers for Radar Observation v1 (no HTTP / no DB)."""

from __future__ import annotations

import json

from app.schemas.radar_fingerprint import (
    RadarFingerprintMismatchError,
    assert_revision_fingerprint_matches,
    compute_revision_fingerprint,
)
from app.schemas.radar_v1 import MAX_OBSERVATION_BYTES, RadarObservationV1


class RadarPayloadTooLargeError(ValueError):
    """Serialized Observation exceeds the contract v1 byte bound."""


class RadarUnsupportedSchemaVersionError(ValueError):
    """Unknown schema_version must fail closed."""


def serialized_observation_bytes(observation: RadarObservationV1) -> bytes:
    return observation.model_dump_json(by_alias=False).encode("utf-8")


def assert_observation_within_size_limit(observation: RadarObservationV1) -> int:
    payload = serialized_observation_bytes(observation)
    size = len(payload)
    if size > MAX_OBSERVATION_BYTES:
        raise RadarPayloadTooLargeError(
            f"observation payload is {size} bytes; max is {MAX_OBSERVATION_BYTES}"
        )
    return size


def validate_observation_contract(observation: RadarObservationV1) -> RadarObservationV1:
    """Validate fingerprint + serialized size for an already-parsed Observation v1."""
    if observation.schema_version != 1:
        raise RadarUnsupportedSchemaVersionError(
            f"unsupported schema_version={observation.schema_version}"
        )
    assert_revision_fingerprint_matches(observation)
    assert_observation_within_size_limit(observation)
    return observation


def parse_observation_payload(raw: dict | bytes | str) -> RadarObservationV1:
    if isinstance(raw, bytes):
        if len(raw) > MAX_OBSERVATION_BYTES:
            raise RadarPayloadTooLargeError(
                f"observation payload is {len(raw)} bytes; max is {MAX_OBSERVATION_BYTES}"
            )
        data = json.loads(raw.decode("utf-8"))
    elif isinstance(raw, str):
        encoded = raw.encode("utf-8")
        if len(encoded) > MAX_OBSERVATION_BYTES:
            raise RadarPayloadTooLargeError(
                f"observation payload is {len(encoded)} bytes; max is {MAX_OBSERVATION_BYTES}"
            )
        data = json.loads(raw)
    else:
        data = raw
    if not isinstance(data, dict):
        raise ValueError("observation payload must be a JSON object")
    version = data.get("schema_version")
    if version != 1:
        raise RadarUnsupportedSchemaVersionError(
            f"unsupported schema_version={version!r}; contract v1 requires schema_version=1"
        )
    observation = RadarObservationV1.model_validate(data)
    return validate_observation_contract(observation)


__all__ = [
    "RadarFingerprintMismatchError",
    "RadarPayloadTooLargeError",
    "RadarUnsupportedSchemaVersionError",
    "assert_observation_within_size_limit",
    "assert_revision_fingerprint_matches",
    "compute_revision_fingerprint",
    "parse_observation_payload",
    "serialized_observation_bytes",
    "validate_observation_contract",
]
