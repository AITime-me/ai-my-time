"""Explicit, bounded Admin projections over the application source of truth."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AttentionItem,
    ConferenceEntry,
    ConsultationRequest,
    DiagnosticReport,
    DiagnosticSession,
    ProfileAnswer,
    Touchpoint,
    User,
    UserIdentity,
)
from app.schemas.admin import (
    AdminAttentionList,
    AdminAttentionView,
    AdminConsultationList,
    AdminConsultationView,
    AdminDashboard,
    AdminDiagnosticView,
    AdminLeadList,
    AdminLeadView,
    AdminPersonDetail,
    AdminPersonContact,
    AdminAnalytics,
)


class AdminLeadReadService:
    """Read-only Admin views; all joins remain server-side and bounded."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        source: str | None = None,
        lifecycle_stage: str | None = None,
        diagnostic_completed: bool | None = None,
        consultation_status: str | None = None,
        communication_status: str | None = None,
        attention_only: bool = False,
        search: str | None = None,
    ) -> AdminLeadList:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be between 1 and 100")
        requested_offset = offset
        users = (await self._session.scalars(select(User).order_by(desc(User.created_at)))).all()
        items: list[AdminLeadView] = []
        for user in users:
            view = await self._lead_view(user)
            if source and view.source != source:
                continue
            if lifecycle_stage and view.lifecycle_stage != lifecycle_stage:
                continue
            if diagnostic_completed is not None and (view.diagnostic_status == "diagnostic_completed") != diagnostic_completed:
                continue
            if consultation_status and view.consultation_status != consultation_status:
                continue
            if communication_status and view.communication_status != communication_status:
                continue
            if attention_only and view.attention_count == 0:
                continue
            if search and not _matches_search(view, search):
                continue
            if offset:
                offset -= 1
                continue
            items.append(view)
            if len(items) == limit:
                break
        return AdminLeadList(items=items, limit=limit, offset=requested_offset)

    async def person(self, user_id: uuid.UUID) -> AdminPersonDetail | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        diagnostics = (await self._session.scalars(
            select(DiagnosticSession).where(DiagnosticSession.user_id == user_id).order_by(desc(DiagnosticSession.created_at))
        )).all()
        profile_rows = (await self._session.scalars(
            select(ProfileAnswer).where(ProfileAnswer.user_id == user_id).order_by(ProfileAnswer.question_code, desc(ProfileAnswer.revision))
        )).all()
        answers: dict[str, object] = {}
        for row in profile_rows:
            answers.setdefault(row.question_code, row.answer_json)
        consultations = (await self._session.scalars(
            select(ConsultationRequest).where(ConsultationRequest.user_id == user_id).order_by(desc(ConsultationRequest.created_at))
        )).all()
        attention = (await self._session.scalars(
            select(AttentionItem).where(AttentionItem.user_id == user_id).order_by(desc(AttentionItem.created_at))
        )).all()
        return AdminPersonDetail(
            person=await self._lead_view(user),
            profile_answers=answers,
            diagnostics=[await self._diagnostic_view(row) for row in diagnostics],
            consultations=[await self._consultation_view(row) for row in consultations],
            attention_items=[await self._attention_view(row) for row in attention],
        )

    async def dashboard(self, *, days: int = 7) -> AdminDashboard:
        if days not in {1, 7, 30}:
            raise ValueError("dashboard days must be 1, 7, or 30")
        since = datetime.now(timezone.utc) - timedelta(days=days)
        new_people = await self._count(User, User.created_at >= since)
        started = await self._count(DiagnosticSession, DiagnosticSession.created_at >= since)
        completed = await self._count(
            DiagnosticSession,
            DiagnosticSession.completed_at.is_not(None),
            DiagnosticSession.completed_at >= since,
        )
        consultations = await self._count(ConsultationRequest, ConsultationRequest.created_at >= since)
        new_consultations = await self._count(ConsultationRequest, ConsultationRequest.status == "new")
        consultations_in_progress = await self._count(
            ConsultationRequest, ConsultationRequest.status.in_(("waiting_response", "scheduled"))
        )
        new_attention = await self._count(
            AttentionItem,
            AttentionItem.consultation_request_id.is_(None),
            AttentionItem.status == "new",
        )
        attention_in_progress = await self._count(
            AttentionItem,
            AttentionItem.consultation_request_id.is_(None),
            AttentionItem.status == "in_progress",
        )
        return AdminDashboard(
            new_people=new_people,
            started_diagnostics=started,
            completed_diagnostics=completed,
            consultation_requests=consultations,
            attention_items=new_attention + attention_in_progress,
            new_consultations=new_consultations,
            consultations_in_progress=consultations_in_progress,
            new_attention_items=new_attention,
            attention_in_progress=attention_in_progress,
            funnel={
                "people": new_people,
                "diagnostic_started": started,
                "diagnostic_completed": completed,
                "consultation_requested": consultations,
            },
        )

    async def analytics(self, *, days: int = 7) -> AdminAnalytics:
        if days not in {1, 7, 30}:
            raise ValueError("analytics days must be 1, 7, or 30")
        since = datetime.now(timezone.utc) - timedelta(days=days)
        people = await self._count(User, User.created_at >= since)
        started = await self._count(DiagnosticSession, DiagnosticSession.created_at >= since)
        completed = await self._count(DiagnosticSession, DiagnosticSession.completed_at.is_not(None), DiagnosticSession.completed_at >= since)
        requests = await self._count(ConsultationRequest, ConsultationRequest.created_at >= since)
        return AdminAnalytics(
            period_days=days, people=people, diagnostic_started=started, diagnostic_completed=completed,
            consultation_requested=requests,
            completion_rate=round(completed / started, 4) if started else None,
            consultation_rate=round(requests / completed, 4) if completed else None,
        )

    async def consultations(
        self,
        *,
        status: str | None = None,
        history: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> AdminConsultationList:
        statement = select(ConsultationRequest)
        if status:
            statement = statement.where(ConsultationRequest.status == status)
        elif history:
            statement = statement.where(ConsultationRequest.status.in_(("completed", "cancelled", "no_show")))
        else:
            statement = statement.where(ConsultationRequest.status.in_(("new", "waiting_response", "scheduled")))
        statement = statement.order_by(desc(ConsultationRequest.created_at)).offset(offset).limit(limit)
        rows = (await self._session.scalars(statement)).all()
        return AdminConsultationList(items=[await self._consultation_view(row) for row in rows], limit=limit, offset=offset)

    async def attention(
        self,
        *,
        status: str | None = None,
        history: bool = False,
        standalone: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> AdminAttentionList:
        statement = select(AttentionItem)
        if status:
            statement = statement.where(AttentionItem.status == status)
        elif history:
            statement = statement.where(AttentionItem.status == "resolved")
        else:
            statement = statement.where(AttentionItem.status.in_(("new", "in_progress")))
        if standalone:
            statement = statement.where(AttentionItem.consultation_request_id.is_(None))
        statement = statement.order_by(AttentionItem.priority, desc(AttentionItem.created_at)).offset(offset).limit(limit)
        rows = (await self._session.scalars(statement)).all()
        return AdminAttentionList(items=[await self._attention_view(row) for row in rows], limit=limit, offset=offset)

    async def _lead_view(self, user: User) -> AdminLeadView:
        touchpoint = await self._session.scalar(
            select(Touchpoint).where(Touchpoint.user_id == user.id).order_by(desc(Touchpoint.observed_at)).limit(1)
        )
        conference = await self._session.scalar(
            select(ConferenceEntry).where(ConferenceEntry.user_id == user.id).order_by(desc(ConferenceEntry.created_at)).limit(1)
        )
        diagnostic = await self._session.scalar(
            select(DiagnosticSession).where(DiagnosticSession.user_id == user.id).order_by(desc(DiagnosticSession.created_at)).limit(1)
        )
        summary: str | None = None
        if diagnostic is not None:
            report = await self._session.scalar(select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == diagnostic.id))
            summary = report.summary if report else None
        consultation = await self._session.scalar(
            select(ConsultationRequest).where(ConsultationRequest.user_id == user.id).order_by(desc(ConsultationRequest.created_at)).limit(1)
        )
        business_type = await self._session.scalar(
            select(ProfileAnswer.answer_json)
            .where(ProfileAnswer.user_id == user.id, ProfileAnswer.question_code == "business_type")
            .order_by(desc(ProfileAnswer.revision))
            .limit(1)
        )
        attention_count = await self._count(
            AttentionItem,
            AttentionItem.user_id == user.id,
            AttentionItem.status.in_(("new", "in_progress")),
        )
        return AdminLeadView(
            user_id=user.id,
            display_name=user.display_name,
            telegram_username=user.telegram_username,
            lifecycle_stage=user.lifecycle_stage,
            source=touchpoint.source_code if touchpoint else None,
            conference_code=conference.conference_code if conference else None,
            diagnostic_status=diagnostic.status if diagnostic else None,
            diagnostic_summary=summary,
            consultation_status=consultation.status if consultation else None,
            business_segment=_answer_value(business_type),
            communication_status=user.communication_status,
            marketing_consent_status=user.marketing_consent_status,
            telegram_reachability=user.telegram_reachability,
            attention_count=attention_count,
            created_at=user.created_at,
            last_activity_at=user.last_activity_at,
        )

    async def _diagnostic_view(self, diagnostic: DiagnosticSession) -> AdminDiagnosticView:
        report = await self._session.scalar(select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == diagnostic.id))
        return AdminDiagnosticView(
            diagnostic_session_id=diagnostic.id,
            status=diagnostic.status,
            created_at=diagnostic.created_at,
            completed_at=diagnostic.completed_at,
            summary=report.summary if report else None,
            result_version=report.result_version if report else None,
            result=report.result_json if report else None,
        )

    async def _consultation_view(self, request: ConsultationRequest) -> AdminConsultationView:
        diagnostic = await self._session.get(DiagnosticSession, request.diagnostic_session_id)
        report = await self._session.scalar(select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == request.diagnostic_session_id))
        touchpoint = await self._session.scalar(
            select(Touchpoint).where(Touchpoint.user_id == request.user_id).order_by(desc(Touchpoint.observed_at)).limit(1)
        )
        return AdminConsultationView(
            consultation_request_id=request.id,
            diagnostic_session_id=request.diagnostic_session_id,
            status=request.status,
            created_at=request.created_at,
            diagnostic_summary=report.summary if report else None,
            source=touchpoint.source_code if touchpoint else None,
            appointment_at=request.appointment_at,
            confirmation_state=request.confirmation_state,
            confirmation_source=request.confirmation_source,
            commercial_result=request.commercial_result,
            origin_type=request.origin_type,
            repeat_task_text=request.repeat_task_text,
            person=await self._person_contact(request.user_id),
        )

    async def _person_contact(self, user_id: uuid.UUID) -> AdminPersonContact:
        user = await self._session.get(User, user_id)
        assert user is not None
        telegram_user_id = await self._session.scalar(
            select(UserIdentity.external_id).where(
                UserIdentity.user_id == user_id,
                UserIdentity.provider == "telegram",
                UserIdentity.connection_scope == "ai_my_time_lead_bot",
            )
        )
        return AdminPersonContact(
            user_id=user.id,
            display_name=user.display_name,
            telegram_username=user.telegram_username,
            telegram_user_id=telegram_user_id,
        )

    async def _attention_view(self, item: AttentionItem) -> AdminAttentionView:
        return AdminAttentionView(
            attention_item_id=item.id,
            kind=item.kind,
            reason=item.reason,
            priority=item.priority,
            status=item.status,
            created_at=item.created_at,
            linked_diagnostic_session_id=item.diagnostic_session_id,
            consultation_request_id=item.consultation_request_id,
            person=await self._person_contact(item.user_id),
        )

    async def _count(self, model, *conditions) -> int:
        value = await self._session.scalar(select(func.count()).select_from(model).where(*conditions))
        return int(value or 0)


def _answer_value(value: object) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("value")
        return str(candidate) if candidate is not None else None
    return str(value) if value is not None else None

def _matches_search(view: AdminLeadView, needle: str) -> bool:
    normalized = needle.strip().casefold()
    if not normalized:
        return True
    values = (str(view.user_id), view.display_name or "", view.telegram_username or "")
    return any(normalized in value.casefold() for value in values)
