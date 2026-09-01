"""Dynamic, bounded Admin audiences. This module deliberately never sends."""
from __future__ import annotations

import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminAuditEvent, AdminSegment, ConferenceEntry, ConsultationRequest,
    DiagnosticSession, ProfileAnswer, Touchpoint, User,
)
from app.schemas.admin import (
    AdminAudienceDetail, AdminAudienceList, AdminAudienceMemberList,
    AdminAudienceMemberView, AdminAudienceView, AudienceConditions,
)


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
