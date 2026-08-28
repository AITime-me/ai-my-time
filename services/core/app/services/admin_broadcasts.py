"""Segments and broadcast drafts with a hard no-send MVP boundary."""
from __future__ import annotations

import uuid

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent, AdminSegment, BroadcastCampaign, DiagnosticSession, OutboundMessage, User
from app.schemas.admin import AdminBroadcastList, AdminBroadcastView, AdminSegmentList, AdminSegmentView
from app.services.outbox import OutboundQueue


class AdminBroadcastService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def segments(self) -> AdminSegmentList:
        rows = (await self._session.scalars(select(AdminSegment).where(AdminSegment.is_active.is_(True)).order_by(AdminSegment.key))).all()
        return AdminSegmentList(items=[AdminSegmentView(segment_id=row.id, key=row.key, title=row.title, eligible_count=await self._count(row)) for row in rows])

    async def broadcasts(self) -> AdminBroadcastList:
        rows = (await self._session.scalars(select(BroadcastCampaign).order_by(BroadcastCampaign.created_at.desc()).limit(100))).all()
        return AdminBroadcastList(items=[await self._view(row) for row in rows])

    async def create_draft(self, *, actor_id: uuid.UUID, segment_id: uuid.UUID, title: str, body: str) -> BroadcastCampaign | None:
        segment = await self._session.get(AdminSegment, segment_id)
        if segment is None or not segment.is_active:
            return None
        row = BroadcastCampaign(segment_id=segment_id, title=title.strip(), body=body.strip(), created_by_actor_id=actor_id)
        self._session.add(row)
        await self._session.flush()
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="broadcast.draft_created", object_type="broadcast_campaign", object_id=row.id, delta_json={"segment_id": str(segment_id), "eligible_count": await self._count(segment)}))
        return row

    async def preview(self, broadcast_id: uuid.UUID) -> AdminBroadcastView | None:
        row = await self._session.get(BroadcastCampaign, broadcast_id)
        return await self._view(row) if row else None

    async def confirm_send(self, *, actor_id: uuid.UUID, broadcast_id: uuid.UUID) -> AdminBroadcastView | None:
        row = await self._session.get(BroadcastCampaign, broadcast_id, with_for_update=True)
        if row is None:
            return None
        if row.status not in {"draft", "queued"}:
            return await self._view(row)
        segment = await self._session.get(AdminSegment, row.segment_id)
        if segment is None:
            return None
        recipients = await self._eligible_users(segment)
        queue = OutboundQueue(self._session)
        for user in recipients:
            # Gating is re-evaluated above at the moment of confirmation.
            await queue.enqueue(user_id=user.id, channel="telegram", payload={"kind": "broadcast", "broadcast_id": str(row.id), "text": row.body}, dedupe_key=f"broadcast:{row.id}:{user.id}")
        row.status = "queued"
        row.approved_at = row.approved_at or datetime.now(timezone.utc)
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="broadcast.send_confirmed", object_type="broadcast_campaign", object_id=row.id, delta_json={"eligible_count": len(recipients), "delivery": "outbox"}))
        return await self._view(row)

    async def _view(self, row: BroadcastCampaign) -> AdminBroadcastView:
        segment = await self._session.get(AdminSegment, row.segment_id)
        prefix = f"broadcast:{row.id}:%"
        async def count(*conditions: object) -> int:
            return int(await self._session.scalar(select(func.count()).select_from(OutboundMessage).where(OutboundMessage.dedupe_key.like(prefix), *conditions)) or 0)
        return AdminBroadcastView(broadcast_id=row.id, segment_id=row.segment_id, title=row.title, body=row.body, status=row.status, eligible_count=await self._count(segment), queued_count=await count(OutboundMessage.status.in_(("pending", "processing"))), sent_count=await count(OutboundMessage.status == "sent"), failed_count=await count(OutboundMessage.status == "failed"), created_at=row.created_at)

    async def _eligible_users(self, segment: AdminSegment) -> list[User]:
        definition = segment.definition_json
        statement = select(User)
        # A launch is always a promotional communication and therefore is fail-closed.
        statement = statement.where(User.marketing_consent_status == "confirmed", User.telegram_reachability == "allowed", User.communication_status == "subscribed")
        if definition.get("diagnostic_completed") is True:
            statement = statement.where(select(DiagnosticSession.id).where(DiagnosticSession.user_id == User.id, DiagnosticSession.completed_at.is_not(None)).exists())
        return (await self._session.scalars(statement)).all()

    async def _count(self, segment: AdminSegment | None) -> int:
        if segment is None:
            return 0
        statement = select(func.count()).select_from(User)
        definition = segment.definition_json
        if definition.get("marketing_consent") == "confirmed":
            statement = statement.where(User.marketing_consent_status == "confirmed", User.telegram_reachability == "allowed", User.communication_status == "subscribed")
        if definition.get("diagnostic_completed") is True:
            statement = statement.where(select(DiagnosticSession.id).where(DiagnosticSession.user_id == User.id, DiagnosticSession.completed_at.is_not(None)).exists())
        return int(await self._session.scalar(statement) or 0)
