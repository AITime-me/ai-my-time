"""Unit + optional PostgreSQL proofs for shadow-trial observation export."""

from __future__ import annotations

import asyncio
import json
import os
import stat
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import session_scope
from app.models import RadarObservationReceipt, RadarReader, RadarSource, RadarTenant
from scripts.export_radar_trial_report import (
    ALLOWED_OUTPUT_KEYS,
    FORBIDDEN_OUTPUT_KEYS,
    MAX_WINDOW,
    TrialExportError,
    assert_safe_record,
    build_records,
    export_trial_report,
    extract_text,
    parse_utc,
    summarize,
    truncate_text,
    validate_window,
    write_jsonl,
)


def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 11, hour, minute, tzinfo=timezone.utc)


def _receipt(
    *,
    tenant_id: uuid.UUID,
    source_id: uuid.UUID,
    message_id: str,
    detected_at: datetime,
    origin: str = "live",
    text_value: str = "radar-canary-1011 need CRM",
    receipt_id: uuid.UUID | None = None,
) -> RadarObservationReceipt:
    return RadarObservationReceipt(
        id=receipt_id or uuid.uuid4(),
        tenant_id=tenant_id,
        reader_id=uuid.uuid4(),
        source_id=source_id,
        observation_id=uuid.uuid4(),
        manifest_version="test",
        message_id=message_id,
        revision_fingerprint="a" * 64,
        payload_sha256="b" * 64,
        event_kind="message_upsert",
        origin=origin,
        published_at=detected_at,
        detected_at=detected_at,
        payload={
            "content": {"kind": "text", "text": text_value},
            "author": {
                "id": "999001",
                "username": "secret_user",
                "display_name": "Secret Person",
                "author_type": "user",
            },
            "links": {"message_url_status": "unavailable", "author_url_status": "unavailable"},
        },
    )


def test_utc_time_window_filtering() -> None:
    """Contract: retain detected_at in [from, to)."""

    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    rows = [
        _receipt(tenant_id=tenant_id, source_id=source_id, message_id="1", detected_at=_ts(9, 59)),
        _receipt(tenant_id=tenant_id, source_id=source_id, message_id="2", detected_at=_ts(10, 0)),
        _receipt(tenant_id=tenant_id, source_id=source_id, message_id="3", detected_at=_ts(11, 59)),
        _receipt(tenant_id=tenant_id, source_id=source_id, message_id="4", detected_at=_ts(12, 0)),
    ]
    from_utc, to_utc = _ts(10), _ts(12)
    retained = [
        row
        for row in rows
        if row.detected_at >= from_utc and row.detected_at < to_utc
    ]
    assert [row.message_id for row in retained] == ["2", "3"]
    records = build_records(retained, max_text_chars=40)
    assert {item["message_id"] for item in records} == {"2", "3"}


def test_invalid_range_rejection() -> None:
    start = _ts(10)
    with pytest.raises(TrialExportError, match="to must be after from"):
        validate_window(from_utc=start, to_utc=start)
    with pytest.raises(TrialExportError, match="to must be after from"):
        validate_window(from_utc=start, to_utc=start - timedelta(seconds=1))
    with pytest.raises(TrialExportError, match="window must be"):
        validate_window(from_utc=start, to_utc=start + MAX_WINDOW + timedelta(seconds=1))
    with pytest.raises(TrialExportError, match="timezone-aware"):
        parse_utc("2026-10-11T10:00:00", field_name="from-utc")


def test_text_truncation_and_extract() -> None:
    payload = {
        "content": {"kind": "text", "text": "abcdefghijklmnopqrstuvwxyz"},
        "author": {"username": "hidden"},
    }
    assert extract_text(payload) == "abcdefghijklmnopqrstuvwxyz"
    assert truncate_text("abcdefghij", max_text_chars=4) == "abcd"
    with pytest.raises(TrialExportError, match="max_text_chars"):
        truncate_text("x", max_text_chars=0)


def test_no_author_participant_fields_in_output() -> None:
    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    receipts = [
        _receipt(
            tenant_id=tenant_id,
            source_id=source_id,
            message_id="7",
            detected_at=_ts(11, 21),
            text_value="radar-canary-1011",
        )
    ]
    records = build_records(receipts, max_text_chars=200)
    assert len(records) == 1
    record = records[0]
    assert frozenset(record) == ALLOWED_OUTPUT_KEYS
    assert frozenset(record).isdisjoint(FORBIDDEN_OUTPUT_KEYS)
    assert_safe_record(record)
    blob = json.dumps(record)
    assert "author" not in blob
    assert "secret_user" not in blob
    assert "Secret Person" not in blob
    assert "999001" not in blob
    assert record["truncated_text"] == "radar-canary-1011"


def test_revision_counting() -> None:
    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    receipts = [
        _receipt(
            tenant_id=tenant_id,
            source_id=source_id,
            message_id="42",
            detected_at=_ts(12, 0),
            receipt_id=first_id,
            text_value="v1",
        ),
        _receipt(
            tenant_id=tenant_id,
            source_id=source_id,
            message_id="42",
            detected_at=_ts(12, 5),
            receipt_id=second_id,
            origin="catch_up",
            text_value="v2 edited",
        ),
        _receipt(
            tenant_id=tenant_id,
            source_id=source_id,
            message_id="43",
            detected_at=_ts(12, 6),
            origin="reconciliation",
            text_value="solo",
        ),
    ]
    records = build_records(receipts, max_text_chars=100)
    by_msg = {(r["message_id"], r["revision_index"]): r for r in records}
    assert by_msg[("42", 1)]["revision_count"] == 2
    assert by_msg[("42", 1)]["is_latest_revision"] is False
    assert by_msg[("42", 2)]["is_latest_revision"] is True
    assert by_msg[("43", 1)]["revision_count"] == 1
    summary = summarize(records)
    assert summary.total_receipts == 3
    assert summary.unique_messages == 2
    assert summary.live == 1
    assert summary.catch_up == 1
    assert summary.reconciliation == 1
    assert summary.revisions == 2
    assert summary.latest_revisions == 2


def test_output_file_permissions_0600(tmp_path: Path) -> None:
    path = tmp_path / "trial.jsonl"
    records = build_records(
        [
            _receipt(
                tenant_id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                message_id="1",
                detected_at=_ts(10),
            )
        ],
        max_text_chars=32,
    )
    write_jsonl(path, records)
    assert path.exists()
    if os.name == "nt":
        pytest.skip("POSIX 0600 not enforceable on Windows NTFS the same way")
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600


def test_export_sets_transaction_read_only(tmp_path: Path) -> None:
    executed: list[str] = []

    class _Result:
        def all(self) -> list[RadarObservationReceipt]:
            return []

    class _Begin:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *args: object) -> None:
            return None

    class _Session:
        def begin(self) -> _Begin:
            return _Begin()

        async def execute(self, statement: object, *args: object, **kwargs: object) -> None:
            executed.append(str(statement))

        async def scalars(self, statement: object) -> _Result:
            executed.append(str(statement))
            return _Result()

        async def __aenter__(self) -> _Session:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    def factory() -> _Session:
        return _Session()

    summary = asyncio.run(
        export_trial_report(
            factory,  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            from_utc=_ts(10),
            to_utc=_ts(11),
            max_text_chars=100,
            output_path=tmp_path / "empty.jsonl",
        )
    )
    assert summary.total_receipts == 0
    assert any("SET TRANSACTION READ ONLY" in item for item in executed)
    assert not any(
        token in item.upper()
        for item in executed
        for token in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ")
    )


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_tenant_source_and_window_isolation_integration(tmp_path: Path) -> None:
    asyncio.run(_run_isolation(_test_database_url(), tmp_path))


def test_read_only_rejects_writes_integration() -> None:
    asyncio.run(_run_read_only_guard(_test_database_url()))


async def _seed_pair(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    await session.execute(
        text(
            "TRUNCATE TABLE radar_alert_outbox, radar_signal, radar_observation_receipt, "
            "radar_profile_source, radar_search_rule, radar_profile_version, radar_search_profile, "
            "radar_source, radar_reader, radar_tenant RESTART IDENTITY CASCADE"
        )
    )
    tenant_a = RadarTenant(slug="trial-a")
    tenant_b = RadarTenant(slug="trial-b")
    session.add_all([tenant_a, tenant_b])
    await session.flush()
    reader_a = RadarReader(
        tenant_id=tenant_a.id,
        reader_key="trial-a",
        credential_key_id="rk_trial_a",
    )
    reader_b = RadarReader(
        tenant_id=tenant_b.id,
        reader_key="trial-b",
        credential_key_id="rk_trial_b",
    )
    session.add_all([reader_a, reader_b])
    await session.flush()
    source_a1 = RadarSource(
        tenant_id=tenant_a.id,
        reader_id=reader_a.id,
        peer_type="supergroup",
        peer_id=4300847797,
        source_type="supergroup",
        is_approved=True,
        monitoring_capability="realtime",
    )
    source_a2 = RadarSource(
        tenant_id=tenant_a.id,
        reader_id=reader_a.id,
        peer_type="channel",
        peer_id=111,
        source_type="channel",
        is_approved=True,
        monitoring_capability="realtime",
    )
    source_b = RadarSource(
        tenant_id=tenant_b.id,
        reader_id=reader_b.id,
        peer_type="supergroup",
        peer_id=4300847797,
        source_type="supergroup",
        is_approved=True,
        monitoring_capability="realtime",
    )
    session.add_all([source_a1, source_a2, source_b])
    await session.flush()

    rows = [
        _receipt(
            tenant_id=tenant_a.id,
            source_id=source_a1.id,
            message_id="7",
            detected_at=_ts(11, 21),
            text_value="radar-canary-1011 in window",
        ),
        _receipt(
            tenant_id=tenant_a.id,
            source_id=source_a1.id,
            message_id="8",
            detected_at=_ts(9, 0),
            text_value="too early",
        ),
        _receipt(
            tenant_id=tenant_a.id,
            source_id=source_a2.id,
            message_id="9",
            detected_at=_ts(11, 30),
            text_value="other source",
        ),
        _receipt(
            tenant_id=tenant_b.id,
            source_id=source_b.id,
            message_id="7",
            detected_at=_ts(11, 21),
            text_value="other tenant",
        ),
    ]
    for row in rows:
        row.reader_id = reader_a.id if row.tenant_id == tenant_a.id else reader_b.id
        session.add(row)
    await session.flush()
    return tenant_a.id, source_a1.id, tenant_b.id, source_b.id


async def _run_isolation(database_url: str, tmp_path: Path) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_scope(factory) as session:
            tenant_a, source_a1, _tenant_b, _source_b = await _seed_pair(session)

        output = tmp_path / "canary-window.jsonl"
        summary = await export_trial_report(
            factory,
            tenant_id=tenant_a,
            source_id=source_a1,
            from_utc=_ts(10),
            to_utc=_ts(12),
            max_text_chars=80,
            output_path=output,
        )
        assert summary.total_receipts == 1
        assert summary.unique_messages == 1
        lines = output.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["message_id"] == "7"
        assert record["truncated_text"] == "radar-canary-1011 in window"
        assert "author" not in record
        assert "secret_user" not in json.dumps(record)

        empty_summary = await export_trial_report(
            factory,
            tenant_id=tenant_a,
            source_id=uuid.uuid4(),
            from_utc=_ts(10),
            to_utc=_ts(12),
            max_text_chars=80,
            output_path=tmp_path / "empty-source.jsonl",
        )
        assert empty_summary.total_receipts == 0
    finally:
        await engine.dispose()


async def _run_read_only_guard(database_url: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            async with session.begin():
                await session.execute(text("SET TRANSACTION READ ONLY"))
                with pytest.raises(Exception):
                    await session.execute(
                        text(
                            "INSERT INTO radar_tenant (id, slug, enabled, raw_retention_days, "
                            "metadata_retention_days, created_at, updated_at) "
                            "VALUES (gen_random_uuid(), 'readonly-probe', true, 30, 90, now(), now())"
                        )
                    )
    finally:
        await engine.dispose()
