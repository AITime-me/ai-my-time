"""Segments and broadcast drafts with a hard no-send MVP boundary."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent, AdminSegment, BroadcastCampaign, DiagnosticSession, User
from app.schemas.admin import AdminBroadcastList, AdminBroadcastView, AdminSegmentList, AdminSegmentView


class AdminBroadcastService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def segments(self) -> AdminSegmentList:
        rows = (await self._session.scalars(select(AdminSegment).where(AdminSegment.is_active.is_(True)).order_by(AdminSegment.key))).all()
        return AdminSegmentList(items=[AdminSegmentView(segment_id=row.id, key=row.key, title=row.title, eligible_count=await self._count(row)) for row in rows])

    async def broadcasts(self) -> AdminBroadcastList:
        rows = (await self._session.scalars(select(BroadcastCampaign).order_by(BroadcastCampaign.created_at.desc()).limit(100))).all()
        return AdminBroadcastList(items=[AdminBroadcastView(broadcast_id=row.id, segment_id=row.segment_id, title=row.title, body=row.body, status=row.status, eligible_count=await self._count(await self._session.get(AdminSegment, row.segment_id)), created_at=row.created_at) for row in rows])

    async def create_draft(self, *, actor_id: uuid.UUID, segment_id: uuid.UUID, title: str, body: str) -> BroadcastCampaign | None:
        segment = await self._session.get(AdminSegment, segment_id)
        if segment is None or not segment.is_active:
            return None
        row = BroadcastCampaign(segment_id=segment_id, title=title.strip(), body=body.strip(), created_by_actor_id=actor_id)
        self._session.add(row)
        await self._session.flush()
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="broadcast.draft_created", object_type="broadcast_campaign", object_id=row.id, delta_json={"segment_id": str(segment_id), "eligible_count": await self._count(segment)}))
        return row

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
