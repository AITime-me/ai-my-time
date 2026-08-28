"""Closed internal support for a one-use Diagnostic AI acceptance restart."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosticAcceptanceGrant, LeadBotSession, User
from app.services.lead_profile_flow import LeadProfileFlow

_PREFIX = "acceptance_"


def is_acceptance_start(entry_code: str) -> bool:
    return entry_code.startswith(_PREFIX) and len(entry_code) > len(_PREFIX)


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("ascii")).hexdigest()


def _flow_snapshot(flow: LeadBotSession) -> dict[str, object]:
    return {
        "id": str(flow.id),
        "user_id": str(flow.user_id),
        "state": flow.state,
        "status": flow.status,
        "version": flow.version,
        "flow_version": flow.flow_version,
        "created_at": flow.created_at.isoformat() if flow.created_at else None,
        "updated_at": flow.updated_at.isoformat() if flow.updated_at else None,
    }


@dataclass(frozen=True)
class IssuedAcceptanceGrant:
    raw_start_parameter: str
    grant_id: uuid.UUID
    expires_at: datetime


class DiagnosticAcceptanceService:
    """Issues and consumes acceptance-only grants; it has no normal-flow path."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, *, user_id: uuid.UUID, ttl: timedelta) -> IssuedAcceptanceGrant:
        if ttl <= timedelta():
            raise ValueError("acceptance grant TTL must be positive")
        now = datetime.now(timezone.utc)
        # The grant is an operator-only action, but lock the bound user anyway:
        # two concurrent invocations must not issue two usable links.
        user = await self._session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise ValueError("user not found")
        active = await self._session.scalar(
            select(DiagnosticAcceptanceGrant.id).where(
                DiagnosticAcceptanceGrant.user_id == user_id,
                DiagnosticAcceptanceGrant.consumed_at.is_(None),
                DiagnosticAcceptanceGrant.expires_at > now,
            ).limit(1)
        )
        if active is not None:
            raise ValueError("an active acceptance grant already exists for this user")
        raw_token = secrets.token_urlsafe(24)
        grant = DiagnosticAcceptanceGrant(
            user_id=user_id,
            token_hash=_token_hash(raw_token),
            expires_at=now + ttl,
        )
        self._session.add(grant)
        await self._session.flush()
        return IssuedAcceptanceGrant(
            raw_start_parameter=f"{_PREFIX}{raw_token}",
            grant_id=grant.id,
            expires_at=grant.expires_at,
        )

    async def consume_and_restart(self, *, user_id: uuid.UUID, entry_code: str) -> bool:
        """Atomically consume a user-bound grant and reopen the current v2 flow.

        A failed or repeated link is a strict no-op.  The successful transition
        updates only the current lead-flow projection; DiagnosticSession,
        reports, turns and their snapshots are not touched.
        """
        if not is_acceptance_start(entry_code):
            return False
        raw_token = entry_code.removeprefix(_PREFIX)
        now = datetime.now(timezone.utc)
        flow = await self._session.scalar(
            select(LeadBotSession)
            .where(LeadBotSession.user_id == user_id)
            .with_for_update()
        )
        if flow is None or flow.flow_version != "v2" or flow.status != "completed":
            return False
        result = await self._session.execute(
            update(DiagnosticAcceptanceGrant)
            .where(
                DiagnosticAcceptanceGrant.user_id == user_id,
                DiagnosticAcceptanceGrant.token_hash == _token_hash(raw_token),
                DiagnosticAcceptanceGrant.consumed_at.is_(None),
                DiagnosticAcceptanceGrant.expires_at > now,
            )
            .values(consumed_at=now, prior_flow_snapshot_json=_flow_snapshot(flow))
            .returning(DiagnosticAcceptanceGrant.id)
        )
        if result.scalar_one_or_none() is None:
            return False
        await LeadProfileFlow(self._session).restart_completed_v2_for_acceptance(flow)
        return True
