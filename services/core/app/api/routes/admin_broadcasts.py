from fastapi import APIRouter, HTTPException, Request
from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminBroadcastDraftCreate, AdminBroadcastList, AdminBroadcastView, AdminSegmentList
from app.services.admin_broadcasts import AdminBroadcastService

router = APIRouter(prefix="/admin", tags=["admin-broadcasts"])

@router.get("/segments", response_model=AdminSegmentList)
async def segments(request: Request) -> AdminSegmentList:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session: return await AdminBroadcastService(session).segments()

@router.get("/broadcasts", response_model=AdminBroadcastList)
async def broadcasts(request: Request) -> AdminBroadcastList:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session: return await AdminBroadcastService(session).broadcasts()

@router.post("/broadcasts/drafts", response_model=AdminBroadcastView, status_code=201)
async def draft(payload: AdminBroadcastDraftCreate, request: Request) -> AdminBroadcastView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        service = AdminBroadcastService(session); row = await service.create_draft(actor_id=actor.user_id, **payload.model_dump())
        if row is None: raise HTTPException(status_code=404, detail="segment not found")
        count = next(item.eligible_count for item in (await service.segments()).items if item.segment_id == row.segment_id)
        return AdminBroadcastView(broadcast_id=row.id, segment_id=row.segment_id, title=row.title, body=row.body, status=row.status, eligible_count=count, created_at=row.created_at)
