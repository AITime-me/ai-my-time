"""Unit proofs for Reader bearer parsing and credential store reload."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.radar_reader_auth import RadarReaderUnauthorizedError, parse_reader_bearer
from app.services.radar_reader_credentials import (
    RadarCredentialStoreUnavailableError,
    RadarReaderCredentialStore,
)


def test_parse_reader_bearer_accepts_key_secret() -> None:
    key, secret = parse_reader_bearer("Bearer key-1.supersecretvalue")
    assert key == "key-1"
    assert secret == "supersecretvalue"


@pytest.mark.parametrize(
    "header",
    [None, "", "Basic x", "Bearer onlykey", "bearer key.secret", "Bearer .secret", "Bearer key."],
)
def test_parse_reader_bearer_rejects_bad_format(header: str | None) -> None:
    with pytest.raises(RadarReaderUnauthorizedError):
        parse_reader_bearer(header)


def test_parse_reader_bearer_allows_dot_inside_secret() -> None:
    key, secret = parse_reader_bearer("Bearer key-1.sec.ret.value")
    assert key == "key-1"
    assert secret == "sec.ret.value"


def test_credential_store_reloads_on_mtime_change(tmp_path: Path) -> None:
    import os
    import time

    path = tmp_path / "creds.json"
    path.write_text(json.dumps({"k1": "secret-one"}), encoding="utf-8")
    store = RadarReaderCredentialStore()
    assert store.lookup(path=str(path), credential_key_id="k1") == "secret-one"
    path.write_text(json.dumps({"k1": "secret-two"}), encoding="utf-8")
    # Windows can keep the same mtime_ns for back-to-back writes.
    now = time.time() + 1
    os.utime(path, (now, now))
    assert store.lookup(path=str(path), credential_key_id="k1") == "secret-two"


def test_credential_store_missing_path_unavailable(tmp_path: Path) -> None:
    store = RadarReaderCredentialStore()
    with pytest.raises(RadarCredentialStoreUnavailableError):
        store.lookup(path=str(tmp_path / "missing.json"), credential_key_id="k1")


def test_manifest_version_is_deterministic() -> None:
    from datetime import datetime, timezone
    import uuid

    from app.models import RadarSource
    from app.services.radar_config import RadarConfigService

    reader_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source = RadarSource(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        tenant_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        reader_id=reader_id,
        peer_type="channel",
        peer_id=123,
        source_type="channel",
        monitoring_capability="realtime",
        config_version=2,
        enabled=True,
        is_approved=True,
        activated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    a = RadarConfigService.compute_manifest_version(reader_id=reader_id, sources=[source])
    b = RadarConfigService.compute_manifest_version(reader_id=reader_id, sources=[source])
    assert a == b
    assert len(a) == 64
