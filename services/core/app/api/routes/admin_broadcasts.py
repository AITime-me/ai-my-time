import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminBroadcastDraftCreate, AdminBroadcastList, AdminBroadcastView, AdminSegmentList
from app.services.admin_broadcasts import AdminBroadcastService

router = APIRouter(prefix="/admin", tags=["admin-broadcasts"])

@router.get("/segments", response_model=AdminSegmentList)
async def segments(request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminSegmentList:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session: return await AdminBroadcastService(session).segments(limit=limit, offset=offset)

@router.get("/broadcasts", response_model=AdminBroadcastList)
async def broadcasts(request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminBroadcastList:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session: return await AdminBroadcastService(session).broadcasts(limit=limit, offset=offset)

@router.post("/broadcasts/drafts", response_model=AdminBroadcastView, status_code=201)
async def draft(payload: AdminBroadcastDraftCreate, request: Request) -> AdminBroadcastView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        service = AdminBroadcastService(session); row = await service.create_draft(actor_id=actor.user_id, **payload.model_dump())
        if row is None: raise HTTPException(status_code=404, detail="segment not found")
        count = next(item.eligible_count for item in (await service.segments()).items if item.segment_id == row.segment_id)
        return AdminBroadcastView(broadcast_id=row.id, segment_id=row.segment_id, title=row.title, body=row.body, status=row.status, eligible_count=count, queued_count=0, sent_count=0, failed_count=0, created_at=row.created_at)

@router.get("/broadcasts/{broadcast_id}/preview", response_model=AdminBroadcastView)
async def preview(broadcast_id: uuid.UUID, request: Request) -> AdminBroadcastView:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminBroadcastService(session).preview(broadcast_id)
        if row is None: raise HTTPException(status_code=404, detail="broadcast not found")
        return row

@router.post("/broadcasts/{broadcast_id}/confirm-send", response_model=AdminBroadcastView)
async def confirm_send(broadcast_id: uuid.UUID, request: Request) -> AdminBroadcastView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminBroadcastService(session).confirm_send(actor_id=actor.user_id, broadcast_id=broadcast_id)
        if row is None: raise HTTPException(status_code=404, detail="broadcast not found")
        return row
