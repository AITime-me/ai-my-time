"""Cookie-protected Admin business projections and narrow action endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import (
    AdminAttentionList,
    AdminTelegramMessage,
    AdminAnalytics,
    AdminConsentUpdate,
    AdminConsultationList,
    AdminDashboard,
    AdminLeadList,
    AdminPersonDetail,
    AdminStatusUpdate,
)
from app.services.admin_actions import AdminActionService
from app.services.admin_read import AdminLeadReadService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/people", response_model=AdminLeadList)
@router.get("/leads", response_model=AdminLeadList, include_in_schema=False)
async def list_recent_leads(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    lifecycle_stage: str | None = None,
    diagnostic_completed: bool | None = None,
    consultation_status: str | None = None,
    communication_status: str | None = None,
    attention_only: bool = False,
    search: str | None = Query(default=None, max_length=256),
) -> AdminLeadList:
    """Return the intentionally minimal lead projection to an authenticated Admin."""
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            return await AdminLeadReadService(session).list_recent(
                limit=limit,
                offset=offset,
                source=source,
                lifecycle_stage=lifecycle_stage,
                diagnostic_completed=diagnostic_completed,
                consultation_status=consultation_status,
                communication_status=communication_status,
                attention_only=attention_only,
                search=search,
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid limit") from None


@router.get("/dashboard", response_model=AdminDashboard)
async def dashboard(request: Request, days: int = Query(default=7)) -> AdminDashboard:
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            return await AdminLeadReadService(session).dashboard(days=days)
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid period") from None


@router.get("/analytics", response_model=AdminAnalytics)
async def analytics(request: Request, days: int = Query(default=7)) -> AdminAnalytics:
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            return await AdminLeadReadService(session).analytics(days=days)
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid period") from None


@router.get("/people/{user_id}", response_model=AdminPersonDetail)
async def person(user_id: uuid.UUID, request: Request) -> AdminPersonDetail:
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        result = await AdminLeadReadService(session).person(user_id)
        if result is None:
            raise HTTPException(status_code=404, detail="person not found")
        return result


@router.patch("/people/{user_id}/marketing-consent", response_model=AdminPersonDetail)
async def update_marketing_consent(
    user_id: uuid.UUID, payload: AdminConsentUpdate, request: Request
) -> AdminPersonDetail:
    actor = await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            changed = await AdminActionService(session).set_marketing_consent(
                actor_id=actor.user_id, user_id=user_id, status=payload.status
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid marketing consent") from None
        if changed is None:
            raise HTTPException(status_code=404, detail="person not found")
        result = await AdminLeadReadService(session).person(user_id)
        assert result is not None
        return result


@router.post("/people/{user_id}/telegram-message", status_code=202)
async def queue_telegram_message(
    user_id: uuid.UUID, payload: AdminTelegramMessage, request: Request
) -> None:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        queued = await AdminActionService(session).queue_telegram_message(
            actor_id=actor.user_id, user_id=user_id, text=payload.text
        )
        if not queued:
            raise HTTPException(status_code=409, detail="Telegram contact is unavailable")


@router.get("/consultations", response_model=AdminConsultationList)
async def consultations(request: Request, status: str | None = None, history: bool = False, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminConsultationList:
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        return await AdminLeadReadService(session).consultations(status=status, history=history, limit=limit, offset=offset)


@router.get("/attention", response_model=AdminAttentionList)
async def attention(request: Request, status: str | None = None, history: bool = False, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminAttentionList:
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        return await AdminLeadReadService(session).attention(status=status, history=history, limit=limit, offset=offset)


@router.patch("/consultations/{request_id}", response_model=AdminConsultationList)
async def update_consultation(request_id: uuid.UUID, payload: AdminStatusUpdate, request: Request) -> AdminConsultationList:
    actor = await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            changed = await AdminActionService(session).set_consultation_status(
                actor_id=actor.user_id, request_id=request_id, status=payload.status
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid status") from None
        if changed is None:
            raise HTTPException(status_code=404, detail="consultation not found")
        return await AdminLeadReadService(session).consultations()


@router.patch("/attention/{item_id}", response_model=AdminAttentionList)
async def update_attention(item_id: uuid.UUID, payload: AdminStatusUpdate, request: Request) -> AdminAttentionList:
    actor = await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            changed = await AdminActionService(session).set_attention_status(
                actor_id=actor.user_id, item_id=item_id, status=payload.status
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid status") from None
        if changed is None:
            raise HTTPException(status_code=404, detail="attention item not found")
        return await AdminLeadReadService(session).attention()
