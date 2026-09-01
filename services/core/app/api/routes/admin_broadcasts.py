import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminAudienceCreate, AdminAudienceDetail, AdminAudienceList, AdminAudienceMemberList, AdminAudienceView
from app.services.admin_broadcasts import AdminAudienceService

router = APIRouter(prefix="/admin", tags=["admin-audiences"])

async def owner_actor(request: Request):
    actor = await current_actor(request)
    if actor.role != "owner":
        raise HTTPException(status_code=403, detail="owner role required")
    return actor

@router.get("/audiences", response_model=AdminAudienceList)
async def audiences(request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminAudienceList:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return await AdminAudienceService(session).audiences(limit=limit, offset=offset)

@router.post("/audiences", response_model=AdminAudienceView, status_code=201)
async def create_audience(payload: AdminAudienceCreate, request: Request) -> AdminAudienceView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminAudienceService(session).create(actor_id=actor.user_id, **payload.model_dump())
        return await AdminAudienceService(session)._view(row)

@router.get("/audiences/{audience_id}", response_model=AdminAudienceDetail)
async def audience(audience_id: uuid.UUID, request: Request) -> AdminAudienceDetail:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminAudienceService(session).audience(audience_id)
        if row is None: raise HTTPException(status_code=404, detail="audience not found")
        return row

@router.patch("/audiences/{audience_id}", response_model=AdminAudienceView)
async def update_audience(audience_id: uuid.UUID, payload: AdminAudienceCreate, request: Request) -> AdminAudienceView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        service = AdminAudienceService(session)
        row = await service.update(actor_id=actor.user_id, audience_id=audience_id, **payload.model_dump())
        if row is None: raise HTTPException(status_code=404, detail="audience not found or is system managed")
        return await service._view(row)

@router.delete("/audiences/{audience_id}", status_code=204)
async def delete_audience(audience_id: uuid.UUID, request: Request) -> Response:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        if not await AdminAudienceService(session).delete(actor_id=actor.user_id, audience_id=audience_id):
            raise HTTPException(status_code=404, detail="audience not found or is system managed")
    return Response(status_code=204)

@router.get("/audiences/{audience_id}/members", response_model=AdminAudienceMemberList)
async def audience_members(audience_id: uuid.UUID, request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminAudienceMemberList:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminAudienceService(session).members(audience_id=audience_id, limit=limit, offset=offset)
        if row is None: raise HTTPException(status_code=404, detail="audience not found")
        return row
