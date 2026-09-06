"""Dynamic, bounded Admin audiences. This module deliberately never sends."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditEvent, AdminSegment, BroadcastCampaign, CampaignRecipient, ConferenceEntry, ConsultationRequest,
    DiagnosticSession, OutboundMessage, ProfileAnswer, Touchpoint, User, UserIdentity,
)
from app.schemas.admin import (
    AdminAudienceDetail, AdminAudienceList, AdminAudienceMemberList,
    AdminAudienceMemberView, AdminAudienceView, AudienceConditions, AdminBroadcastList, AdminBroadcastView,
)
from app.services.outbox import OutboundQueue


class AdminAudienceService:
    """Evaluate allow-listed conditions against the existing lead model at read time."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def audiences(self, *, limit: int = 100, offset: int = 0) -> AdminAudienceList:
        rows = (await self._session.scalars(
            select(AdminSegment).where(AdminSegment.is_active.is_(True)).order_by(AdminSegment.is_system.desc(), AdminSegment.created_at, AdminSegment.key).offset(offset).limit(limit)
        )).all()
        return AdminAudienceList(items=[await self._view(row) for row in rows], limit=limit, offset=offset)

    async def audience(self, audience_id: uuid.UUID) -> AdminAudienceDetail | None:
        row = await self._session.get(AdminSegment, audience_id)
        if row is None or not row.is_active:
            return None
        return AdminAudienceDetail(**(await self._view(row)).model_dump(), conditions=AudienceConditions.model_validate(row.definition_json))

    async def options(self) -> dict[str, list[str]]:
        """Return only data-backed choices and domain-allowed states for the Admin form."""
        touchpoints = (await self._session.scalars(select(Touchpoint))).all()
        conferences = (await self._session.scalars(select(ConferenceEntry.conference_code))).all()
        business_answers = (await self._session.scalars(
            select(ProfileAnswer.answer_json).where(ProfileAnswer.question_code == "business_type")
        )).all()
        sources = {row.source_code for row in touchpoints if row.source_code}
        campaigns = {
            row.metadata_json.get("campaign") for row in touchpoints
            if isinstance(row.metadata_json.get("campaign"), str) and row.metadata_json["campaign"]
        }
        campaigns.update(code for code in conferences if code)
        businesses = {
            answer.get("value") for answer in business_answers
            if isinstance(answer, dict) and isinstance(answer.get("value"), str) and answer["value"]
        }
        return {
            "source_codes": sorted(sources),
            "campaign_codes": sorted(campaigns),
            "business_segments": sorted(businesses),
            "diagnostic_stages": ["prepared", "diagnostic_active", "diagnostic_completed"],
            "consultation_statuses": ["new", "waiting_response", "scheduled", "completed", "cancelled", "no_show"],
        }

    async def create(self, *, actor_id: uuid.UUID, title: str, conditions: AudienceConditions) -> AdminSegment:
        row = AdminSegment(key=f"audience-{uuid.uuid4().hex}", title=title.strip(), definition_json=conditions.model_dump(mode="json", exclude_none=True))
        self._session.add(row)
        await self._session.flush()
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="audience.created", object_type="admin_segment", object_id=row.id, delta_json={"title": row.title, "conditions": row.definition_json}))
        return row

    async def update(self, *, actor_id: uuid.UUID, audience_id: uuid.UUID, title: str, conditions: AudienceConditions) -> AdminSegment | None:
        row = await self._session.get(AdminSegment, audience_id, with_for_update=True)
        if row is None or not row.is_active or row.is_system:
            return None
        row.title = title.strip()
        row.definition_json = conditions.model_dump(mode="json", exclude_none=True)
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="audience.updated", object_type="admin_segment", object_id=row.id, delta_json={"title": row.title, "conditions": row.definition_json}))
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete(self, *, actor_id: uuid.UUID, audience_id: uuid.UUID) -> bool:
        row = await self._session.get(AdminSegment, audience_id, with_for_update=True)
        if row is None or not row.is_active or row.is_system:
            return False
        row.is_active = False
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="audience.deleted", object_type="admin_segment", object_id=row.id, delta_json={"title": row.title}))
        return True

    async def members(self, *, audience_id: uuid.UUID, limit: int, offset: int) -> AdminAudienceMemberList | None:
        row = await self._session.get(AdminSegment, audience_id)
        if row is None or not row.is_active:
            return None
        matches = await self._matching_users(AudienceConditions.model_validate(row.definition_json))
        page = matches[offset : offset + limit]
        return AdminAudienceMemberList(
            audience_id=audience_id,
            total_count=len(matches),
            items=[AdminAudienceMemberView(user_id=x.id, display_name=x.display_name, telegram_username=x.telegram_username, created_at=x.created_at) for x in page],
            limit=limit, offset=offset,
        )

    async def _view(self, row: AdminSegment) -> AdminAudienceView:
        count = len(await self._matching_users(AudienceConditions.model_validate(row.definition_json)))
        return AdminAudienceView(audience_id=row.id, key=row.key, title=row.title, is_system=row.is_system, current_count=count, created_at=row.created_at, updated_at=row.updated_at)

    async def _matching_users(self, conditions: AudienceConditions) -> list[User]:
        users = (await self._session.scalars(select(User).order_by(desc(User.created_at)))).all()
        return [user for user in users if await self._matches(user, conditions)]

    async def matching_users(self, audience: AdminSegment) -> list[User]:
        return await self._matching_users(AudienceConditions.model_validate(audience.definition_json))

    async def _matches(self, user: User, c: AudienceConditions) -> bool:
        if c.content_subscription_status and user.content_subscription_status != c.content_subscription_status:
            return False
        if c.first_seen_from and user.created_at < c.first_seen_from:
            return False
        if c.first_seen_to and user.created_at >= c.first_seen_to:
            return False
        touchpoint = await self._session.scalar(select(Touchpoint).where(Touchpoint.user_id == user.id).order_by(desc(Touchpoint.observed_at)).limit(1))
        conference = await self._session.scalar(select(ConferenceEntry).where(ConferenceEntry.user_id == user.id).order_by(desc(ConferenceEntry.created_at)).limit(1))
        campaign = None
        if touchpoint and isinstance(touchpoint.metadata_json.get("campaign"), str):
            campaign = touchpoint.metadata_json["campaign"]
        if campaign is None and conference:
            campaign = conference.conference_code
        if c.source_codes and (touchpoint is None or touchpoint.source_code not in c.source_codes):
            return False
        if c.campaign_codes and campaign not in c.campaign_codes:
            return False
        business = await self._session.scalar(select(ProfileAnswer.answer_json).where(ProfileAnswer.user_id == user.id, ProfileAnswer.question_code == "business_type").order_by(desc(ProfileAnswer.revision)).limit(1))
        business_value = business.get("value") if isinstance(business, dict) and isinstance(business.get("value"), str) else None
        if c.business_segments and business_value not in c.business_segments:
            return False
        diagnostic = await self._session.scalar(select(DiagnosticSession).where(DiagnosticSession.user_id == user.id).order_by(desc(DiagnosticSession.created_at)).limit(1))
        if c.diagnostic_stages and (diagnostic is None or diagnostic.status not in c.diagnostic_stages):
            return False
        consultation = await self._session.scalar(select(ConsultationRequest).where(ConsultationRequest.user_id == user.id).order_by(desc(ConsultationRequest.created_at)).limit(1))
        if c.consultation_statuses and (consultation is None or consultation.status not in c.consultation_statuses):
            return False
        if c.commercial_results and (consultation is None or consultation.commercial_result not in c.commercial_results):
            return False
        return True


class AdminCampaignService:
    """Content-only campaigns: draft editing, immutable snapshot, durable outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audiences = AdminAudienceService(session)

    async def campaigns(self, *, limit: int = 100, offset: int = 0) -> AdminBroadcastList:
        rows = (await self._session.scalars(select(BroadcastCampaign).order_by(desc(BroadcastCampaign.created_at)).offset(offset).limit(limit))).all()
        return AdminBroadcastList(items=[await self._view(row) for row in rows], limit=limit, offset=offset)

    async def campaign(self, campaign_id: uuid.UUID) -> AdminBroadcastView | None:
        row = await self._session.get(BroadcastCampaign, campaign_id)
        return await self._view(row) if row else None

    async def create(self, *, actor_id: uuid.UUID, segment_id: uuid.UUID, title: str, body: str) -> BroadcastCampaign | None:
        audience = await self._session.get(AdminSegment, segment_id)
        if audience is None or not audience.is_active:
            return None
        row = BroadcastCampaign(segment_id=segment_id, title=title.strip(), body=body.strip(), created_by_actor_id=actor_id)
        self._session.add(row); await self._session.flush()
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="campaign.draft_created", object_type="broadcast_campaign", object_id=row.id, delta_json={"audience_id": str(segment_id)}))
        return row

    async def update(self, *, actor_id: uuid.UUID, campaign_id: uuid.UUID, segment_id: uuid.UUID, title: str, body: str) -> BroadcastCampaign | None:
        row = await self._session.get(BroadcastCampaign, campaign_id, with_for_update=True)
        audience = await self._session.get(AdminSegment, segment_id)
        if row is None or row.status != "draft" or audience is None or not audience.is_active:
            return None
        row.segment_id, row.title, row.body = segment_id, title.strip(), body.strip()
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="campaign.draft_updated", object_type="broadcast_campaign", object_id=row.id, delta_json={"audience_id": str(segment_id)}))
        return row

    async def delete(self, *, actor_id: uuid.UUID, campaign_id: uuid.UUID) -> bool:
        row = await self._session.get(BroadcastCampaign, campaign_id, with_for_update=True)
        if row is None or row.status != "draft": return False
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="campaign.draft_deleted", object_type="broadcast_campaign", object_id=row.id, delta_json={"title": row.title}))
        await self._session.delete(row)
        return True

    async def confirm(self, *, actor_id: uuid.UUID, campaign_id: uuid.UUID) -> AdminBroadcastView | None:
        row = await self._session.get(BroadcastCampaign, campaign_id, with_for_update=True)
        if row is None: return None
        if row.status != "draft": return await self._view(row)
        audience = await self._session.get(AdminSegment, row.segment_id)
        if audience is None or not audience.is_active: return None
        recipients, excluded = await self._recipient_split(audience)
        audience_count = len(recipients) + excluded
        queue = OutboundQueue(self._session)
        queued_count = 0
        for user in recipients:
            # Re-read immediately before outbox intent; the worker performs
            # the final check before any provider call.
            subscribed = await self._session.scalar(
                select(User.content_subscription_status).where(User.id == user.id)
            )
            if subscribed != "subscribed":
                excluded += 1
                continue
            recipient = CampaignRecipient(campaign_id=row.id, user_id=user.id, state="queued")
            self._session.add(recipient); await self._session.flush()
            message = await queue.enqueue(user_id=user.id, channel="telegram_lead", payload={"kind":"content_campaign", "campaign_id":str(row.id), "recipient_id":str(recipient.id), "text":row.body, "buttons":[]}, dedupe_key=f"campaign:{row.id}:user:{user.id}")
            recipient.outbox_message_id = message.id
            queued_count += 1
        now = datetime.now(timezone.utc)
        row.status, row.approved_at, row.snapshot_at = "queued", now, now
        row.audience_count_snapshot = audience_count
        row.excluded_count_snapshot = excluded
        row.audience_snapshot_json = {"audience_id": str(audience.id), "title": audience.title, "conditions": audience.definition_json}
        self._session.add(AdminAuditEvent(actor_id=actor_id, action="campaign.confirmed", object_type="broadcast_campaign", object_id=row.id, delta_json={"recipients":queued_count, "audience_count":audience_count, "excluded":excluded, "snapshot":True}))
        return await self._view(row)

    async def _recipient_split(self, audience: AdminSegment) -> tuple[list[User], int]:
        members = await self._audiences.matching_users(audience)
        eligible: list[User] = []
        for user in members:
            has_telegram = await self._session.scalar(select(UserIdentity.id).where(UserIdentity.user_id == user.id, UserIdentity.provider == "telegram").limit(1))
            if user.content_subscription_status == "subscribed" and has_telegram is not None: eligible.append(user)
        return eligible, len(members) - len(eligible)

    async def _view(self, row: BroadcastCampaign) -> AdminBroadcastView:
        audience = await self._session.get(AdminSegment, row.segment_id)
        if row.snapshot_at is None and audience is not None:
            recipients, excluded = await self._recipient_split(audience); audience_count = len(recipients) + excluded; eligible = len(recipients)
        else:
            eligible = int(await self._session.scalar(select(func.count()).select_from(CampaignRecipient).where(CampaignRecipient.campaign_id == row.id)) or 0)
            audience_count = row.audience_count_snapshot if row.audience_count_snapshot is not None else eligible
            excluded = row.excluded_count_snapshot if row.excluded_count_snapshot is not None else 0
        async def count(statuses: tuple[str, ...]) -> int:
            return int(await self._session.scalar(select(func.count()).select_from(OutboundMessage).where(OutboundMessage.dedupe_key.like(f"campaign:{row.id}:user:%"), OutboundMessage.status.in_(statuses))) or 0)
        skipped = int(await self._session.scalar(select(func.count()).select_from(CampaignRecipient).where(CampaignRecipient.campaign_id == row.id, CampaignRecipient.state == "skipped")) or 0)
        return AdminBroadcastView(broadcast_id=row.id, segment_id=row.segment_id, title=row.title, body=row.body, status=row.status, audience_count=audience_count, eligible_count=eligible, excluded_count=excluded, queued_count=await count(("pending","processing")), sent_count=await count(("sent",)), failed_count=await count(("failed",)), skipped_count=skipped, snapshot_at=row.snapshot_at, created_at=row.created_at)
