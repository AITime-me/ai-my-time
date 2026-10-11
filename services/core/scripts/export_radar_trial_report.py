"""Export a bounded, tenant-scoped Radar observation trial report (read-only).

Operator utility for human shadow-trial review. Not an Admin API, classifier,
or dashboard. Emits JSONL with truncated message text only — never author,
participant, credential, or destination fields.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import RadarObservationReceipt

# Hard ceiling so a mistaken "from epoch" cannot dump the whole table.
MAX_WINDOW = timedelta(hours=48)
ALLOWED_OUTPUT_KEYS = frozenset(
    {
        "message_id",
        "event_kind",
        "origin",
        "published_at",
        "detected_at",
        "revision_index",
        "revision_count",
        "is_latest_revision",
        "truncated_text",
    }
)
FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "author",
        "author_id",
        "username",
        "display_name",
        "participant",
        "phone",
        "credential",
        "destination",
        "chat_id",
        "peer_id",
        "reader_id",
        "observation_id",
        "payload",
        "links",
    }
)


class TrialExportError(ValueError):
    """Invalid operator input or unsafe export bounds."""


@dataclass(frozen=True, slots=True)
class TrialExportSummary:
    total_receipts: int
    unique_messages: int
    live: int
    catch_up: int
    reconciliation: int
    revisions: int
    latest_revisions: int

    def as_dict(self) -> dict[str, int]:
        return {
            "total_receipts": self.total_receipts,
            "unique_messages": self.unique_messages,
            "live": self.live,
            "catch_up": self.catch_up,
            "reconciliation": self.reconciliation,
            "revisions": self.revisions,
            "latest_revisions": self.latest_revisions,
        }


def parse_utc(value: str, *, field_name: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise TrialExportError(f"{field_name} must be an ISO-8601 UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrialExportError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def validate_window(*, from_utc: datetime, to_utc: datetime) -> None:
    if from_utc.tzinfo is None or to_utc.tzinfo is None:
        raise TrialExportError("from/to must be timezone-aware UTC")
    if from_utc.utcoffset() is None or to_utc.utcoffset() is None:
        raise TrialExportError("from/to must be timezone-aware UTC")
    if to_utc <= from_utc:
        raise TrialExportError("to must be after from")
    if (to_utc - from_utc) > MAX_WINDOW:
        raise TrialExportError(
            f"window must be <= {int(MAX_WINDOW.total_seconds() // 3600)} hours"
        )


def extract_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    content = payload.get("content")
    if not isinstance(content, dict):
        return ""
    text_value = content.get("text")
    return text_value if isinstance(text_value, str) else ""


def truncate_text(value: str, *, max_text_chars: int) -> str:
    if max_text_chars < 1:
        raise TrialExportError("max_text_chars must be >= 1")
    if len(value) <= max_text_chars:
        return value
    return value[:max_text_chars]


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_records(
    receipts: Sequence[RadarObservationReceipt],
    *,
    max_text_chars: int,
) -> list[dict[str, object]]:
    """Project receipts into review records with per-message revision metadata."""

    by_message: dict[str, list[RadarObservationReceipt]] = {}
    for receipt in receipts:
        by_message.setdefault(receipt.message_id, []).append(receipt)

    for group in by_message.values():
        group.sort(key=lambda item: (item.detected_at, str(item.id)))

    records: list[dict[str, object]] = []
    for receipt in receipts:
        group = by_message[receipt.message_id]
        revision_index = next(
            index for index, item in enumerate(group, start=1) if item.id == receipt.id
        )
        revision_count = len(group)
        record = {
            "message_id": receipt.message_id,
            "event_kind": receipt.event_kind,
            "origin": receipt.origin,
            "published_at": _iso_or_none(receipt.published_at),
            "detected_at": _iso_or_none(receipt.detected_at),
            "revision_index": revision_index,
            "revision_count": revision_count,
            "is_latest_revision": revision_index == revision_count,
            "truncated_text": truncate_text(
                extract_text(receipt.payload), max_text_chars=max_text_chars
            ),
        }
        assert ALLOWED_OUTPUT_KEYS == frozenset(record)
        records.append(record)

    records.sort(
        key=lambda item: (
            str(item["detected_at"] or ""),
            str(item["message_id"]),
            int(item["revision_index"]),  # type: ignore[arg-type]
        )
    )
    return records


def summarize(records: Sequence[dict[str, object]]) -> TrialExportSummary:
    unique_messages = {str(item["message_id"]) for item in records}
    live = sum(1 for item in records if item["origin"] == "live")
    catch_up = sum(1 for item in records if item["origin"] == "catch_up")
    reconciliation = sum(1 for item in records if item["origin"] == "reconciliation")
    revisions = sum(1 for item in records if int(item["revision_count"]) > 1)  # type: ignore[arg-type]
    latest = sum(1 for item in records if item["is_latest_revision"] is True)
    return TrialExportSummary(
        total_receipts=len(records),
        unique_messages=len(unique_messages),
        live=live,
        catch_up=catch_up,
        reconciliation=reconciliation,
        revisions=revisions,
        latest_revisions=latest,
    )


def assert_safe_record(record: dict[str, object]) -> None:
    keys = frozenset(record)
    unexpected = keys - ALLOWED_OUTPUT_KEYS
    if unexpected:
        raise TrialExportError(f"unexpected output keys: {sorted(unexpected)}")
    leaked = keys & FORBIDDEN_OUTPUT_KEYS
    if leaked:
        raise TrialExportError(f"forbidden field leaked into output: {sorted(leaked)}")
    if keys != ALLOWED_OUTPUT_KEYS:
        raise TrialExportError(f"missing output keys: {sorted(ALLOWED_OUTPUT_KEYS - keys)}")


def write_jsonl(path: Path, records: Sequence[dict[str, object]]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            assert_safe_record(record)
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    if os.name != "nt":
        os.chmod(path, 0o600)
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode != 0o600:
            raise TrialExportError(f"output mode must be 0600, got {oct(mode)}")


async def load_receipts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_id: uuid.UUID,
    from_utc: datetime,
    to_utc: datetime,
) -> list[RadarObservationReceipt]:
    result = await session.scalars(
        select(RadarObservationReceipt)
        .where(
            RadarObservationReceipt.tenant_id == tenant_id,
            RadarObservationReceipt.source_id == source_id,
            RadarObservationReceipt.detected_at >= from_utc,
            RadarObservationReceipt.detected_at < to_utc,
        )
        .order_by(
            RadarObservationReceipt.detected_at.asc(),
            RadarObservationReceipt.message_id.asc(),
            RadarObservationReceipt.id.asc(),
        )
    )
    return list(result.all())


async def export_trial_report(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: uuid.UUID,
    source_id: uuid.UUID,
    from_utc: datetime,
    to_utc: datetime,
    max_text_chars: int,
    output_path: Path,
) -> TrialExportSummary:
    validate_window(from_utc=from_utc, to_utc=to_utc)
    if max_text_chars < 1:
        raise TrialExportError("max_text_chars must be >= 1")

    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("SET TRANSACTION READ ONLY"))
            receipts = await load_receipts(
                session,
                tenant_id=tenant_id,
                source_id=source_id,
                from_utc=from_utc,
                to_utc=to_utc,
            )
            records = build_records(receipts, max_text_chars=max_text_chars)
            summary = summarize(records)
            # Write while still inside the read-only transaction so a later
            # write-path bug cannot mutate DB after export; file I/O is local.
            write_jsonl(output_path, records)
            return summary


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a bounded Radar shadow-trial observation report (PostgreSQL READ ONLY)."
    )
    parser.add_argument("--tenant-id", required=True, type=uuid.UUID)
    parser.add_argument("--source-id", required=True, type=uuid.UUID)
    parser.add_argument("--from-utc", required=True, help="Inclusive UTC ISO-8601 start")
    parser.add_argument("--to-utc", required=True, help="Exclusive UTC ISO-8601 end")
    parser.add_argument("--max-text-chars", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


async def _run(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    from_utc = parse_utc(args.from_utc, field_name="from-utc")
    to_utc = parse_utc(args.to_utc, field_name="to-utc")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        summary = await export_trial_report(
            factory,
            tenant_id=args.tenant_id,
            source_id=args.source_id,
            from_utc=from_utc,
            to_utc=to_utc,
            max_text_chars=args.max_text_chars,
            output_path=args.output,
        )
    finally:
        await engine.dispose()

    print(json.dumps({"summary": summary.as_dict(), "output": str(args.output)}, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    try:
        raise SystemExit(asyncio.run(_run(argv)))
    except TrialExportError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
