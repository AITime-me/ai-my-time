"""Deterministic, Core-side matching for accepted Radar observations."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    RadarObservationReceipt,
    RadarProfileSource,
    RadarProfileVersion,
    RadarSearchProfile,
    RadarSearchRule,
    RadarSignal,
)


@dataclass(frozen=True)
class RadarMatchResult:
    status: str
    matched_rule_keys: list[str]
    excluded_rule_keys: list[str]


def normalize_radar_text(value: str) -> str:
    """Use a stable, locale-independent normal form for v1 term matching."""

    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def rule_matches_text(*, expression: object, normalized_text: str) -> bool:
    """Return true only for a valid non-empty v1 ``terms`` conjunction.

    Unsupported or malformed expressions deliberately do not match.  This keeps
    a newly introduced rule grammar from silently broadening alert delivery.
    """

    if not isinstance(expression, dict):
        return False
    terms = expression.get("terms")
    if not isinstance(terms, list) or not terms:
        return False
    normalized_terms: list[str] = []
    for term in terms:
        if not isinstance(term, str):
            return False
        normalized = normalize_radar_text(term)
        if not normalized:
            return False
        normalized_terms.append(normalized)
    return all(term in normalized_text for term in normalized_terms)


def evaluate_radar_rules(*, text: str, rules: list[RadarSearchRule]) -> RadarMatchResult:
    """Evaluate v1 include/exclude rules with exclusion precedence."""

    normalized_text = normalize_radar_text(text)
    matched = sorted(
        rule.rule_key
        for rule in rules
        if rule.enabled
        and rule.kind == "include"
        and rule_matches_text(expression=rule.expression, normalized_text=normalized_text)
    )
    excluded = sorted(
        rule.rule_key
        for rule in rules
        if rule.enabled
        and rule.kind == "exclude"
        and rule_matches_text(expression=rule.expression, normalized_text=normalized_text)
    )
    if excluded:
        status = "excluded"
    elif matched:
        status = "matched"
    else:
        status = "no_match"
    return RadarMatchResult(status=status, matched_rule_keys=matched, excluded_rule_keys=excluded)


class RadarMatchingService:
    """Materialize at most one durable Signal per tenant/source/message."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def materialize(self, *, receipt: RadarObservationReceipt) -> RadarSignal:
        existing = await self._existing_signal_for_message(receipt)
        if existing is not None:
            prior = await self._session.get(RadarObservationReceipt, existing.observation_receipt_id)
            if prior is not None and prior.revision_fingerprint == receipt.revision_fingerprint:
                # Semantic replay: keep the first Signal; do not create another.
                return existing

        if receipt.event_kind == "message_deleted":
            result = RadarMatchResult("deleted", [], [])
            if existing is not None:
                return await self._update_signal(existing, receipt=receipt, result=result)
            return await self._add_signal(receipt=receipt, result=result)

        versions = (
            await self._session.scalars(
                select(RadarProfileVersion)
                .join(
                    RadarSearchProfile,
                    and_(
                        RadarSearchProfile.tenant_id == RadarProfileVersion.tenant_id,
                        RadarSearchProfile.active_version_id == RadarProfileVersion.id,
                    ),
                )
                .join(
                    RadarProfileSource,
                    and_(
                        RadarProfileSource.tenant_id == RadarProfileVersion.tenant_id,
                        RadarProfileSource.profile_version_id == RadarProfileVersion.id,
                    ),
                )
                .where(
                    RadarProfileVersion.tenant_id == receipt.tenant_id,
                    RadarSearchProfile.enabled.is_(True),
                    RadarProfileSource.source_id == receipt.source_id,
                )
                .order_by(RadarSearchProfile.id)
            )
        ).all()

        # The v1 storage contract intentionally permits one outcome per tenant
        # receipt, rather than one per saved search.  An ambiguous configuration
        # therefore fails closed instead of choosing an arbitrary profile.
        if len(versions) != 1:
            result = RadarMatchResult("no_match", [], [])
            if existing is not None:
                return await self._update_signal(existing, receipt=receipt, result=result)
            return await self._add_signal(receipt=receipt, result=result)

        version = versions[0]
        rules = (
            await self._session.scalars(
                select(RadarSearchRule)
                .where(
                    RadarSearchRule.tenant_id == receipt.tenant_id,
                    RadarSearchRule.profile_version_id == version.id,
                )
                .order_by(RadarSearchRule.rule_key)
            )
        ).all()
        content = receipt.payload.get("content") if isinstance(receipt.payload, dict) else None
        text = content.get("text") if isinstance(content, dict) else None
        result = evaluate_radar_rules(text=text if isinstance(text, str) else "", rules=rules)
        if existing is not None:
            return await self._update_signal(
                existing, receipt=receipt, result=result, profile_version=version
            )
        return await self._add_signal(receipt=receipt, result=result, profile_version=version)

    async def _existing_signal_for_message(
        self, receipt: RadarObservationReceipt
    ) -> RadarSignal | None:
        return await self._session.scalar(
            select(RadarSignal)
            .join(
                RadarObservationReceipt,
                and_(
                    RadarObservationReceipt.tenant_id == RadarSignal.tenant_id,
                    RadarObservationReceipt.id == RadarSignal.observation_receipt_id,
                ),
            )
            .where(
                RadarSignal.tenant_id == receipt.tenant_id,
                RadarObservationReceipt.source_id == receipt.source_id,
                RadarObservationReceipt.message_id == receipt.message_id,
            )
            .order_by(RadarSignal.created_at, RadarSignal.id)
            .limit(1)
        )

    async def _add_signal(
        self,
        *,
        receipt: RadarObservationReceipt,
        result: RadarMatchResult,
        profile_version: RadarProfileVersion | None = None,
    ) -> RadarSignal:
        expires_at = None
        matched_at = None
        if result.status == "matched" and profile_version is not None:
            expires_at = receipt.detected_at + timedelta(seconds=profile_version.freshness_seconds)
            matched_at = datetime.now(timezone.utc)
        signal = RadarSignal(
            tenant_id=receipt.tenant_id,
            observation_receipt_id=receipt.id,
            profile_version_id=profile_version.id if profile_version is not None else None,
            status=result.status,
            matched_rule_keys=result.matched_rule_keys,
            excluded_rule_keys=result.excluded_rule_keys,
            freshness_expires_at=expires_at,
            matched_at=matched_at,
        )
        self._session.add(signal)
        await self._session.flush()
        return signal

    async def _update_signal(
        self,
        signal: RadarSignal,
        *,
        receipt: RadarObservationReceipt,
        result: RadarMatchResult,
        profile_version: RadarProfileVersion | None = None,
    ) -> RadarSignal:
        """Apply a meaningful revision onto the single Signal for this message."""

        signal.observation_receipt_id = receipt.id
        signal.profile_version_id = profile_version.id if profile_version is not None else None
        signal.status = result.status
        signal.matched_rule_keys = result.matched_rule_keys
        signal.excluded_rule_keys = result.excluded_rule_keys
        # First detected_at / freshness window must not be rejuvenated by retries.
        if (
            result.status == "matched"
            and profile_version is not None
            and signal.freshness_expires_at is None
        ):
            signal.freshness_expires_at = receipt.detected_at + timedelta(
                seconds=profile_version.freshness_seconds
            )
            signal.matched_at = datetime.now(timezone.utc)
        elif result.status != "matched":
            # Keep historical matched_at/freshness for audit; status reflects latest.
            pass
        await self._session.flush()
        return signal
