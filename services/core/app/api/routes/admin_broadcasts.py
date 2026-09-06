import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminAudienceCreate, AdminAudienceDetail, AdminAudienceList, AdminAudienceMemberList, AdminAudienceOptions, AdminAudienceView, AdminBroadcastDraftCreate, AdminBroadcastDraftUpdate, AdminBroadcastList, AdminBroadcastView
from app.services.admin_broadcasts import AdminAudienceService, AdminCampaignService

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

@router.get("/audience-options", response_model=AdminAudienceOptions)
async def audience_options(request: Request) -> AdminAudienceOptions:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return AdminAudienceOptions(**(await AdminAudienceService(session).options()))

@router.post("/audiences", response_model=AdminAudienceView, status_code=201)
async def create_audience(payload: AdminAudienceCreate, request: Request) -> AdminAudienceView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminAudienceService(session).create(actor_id=actor.user_id, title=payload.title, conditions=payload.conditions)
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
        row = await service.update(actor_id=actor.user_id, audience_id=audience_id, title=payload.title, conditions=payload.conditions)
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

@router.get("/campaigns", response_model=AdminBroadcastList)
async def campaigns(request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> AdminBroadcastList:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return await AdminCampaignService(session).campaigns(limit=limit, offset=offset)

@router.get("/campaigns/{campaign_id}", response_model=AdminBroadcastView)
async def campaign(campaign_id: uuid.UUID, request: Request) -> AdminBroadcastView:
    await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminCampaignService(session).campaign(campaign_id)
        if row is None: raise HTTPException(status_code=404, detail="campaign not found")
        return row

@router.post("/campaigns", response_model=AdminBroadcastView, status_code=201)
async def create_campaign(payload: AdminBroadcastDraftCreate, request: Request) -> AdminBroadcastView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        service = AdminCampaignService(session); row = await service.create(actor_id=actor.user_id, segment_id=payload.segment_id, title=payload.title, body=payload.body)
        if row is None: raise HTTPException(status_code=404, detail="audience not found")
        return await service.campaign(row.id)  # type: ignore[return-value]

@router.patch("/campaigns/{campaign_id}", response_model=AdminBroadcastView)
async def update_campaign(campaign_id: uuid.UUID, payload: AdminBroadcastDraftUpdate, request: Request) -> AdminBroadcastView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        service = AdminCampaignService(session); row = await service.update(actor_id=actor.user_id, campaign_id=campaign_id, segment_id=payload.segment_id, title=payload.title, body=payload.body)
        if row is None: raise HTTPException(status_code=409, detail="only an existing draft can be edited")
        return await service.campaign(row.id)  # type: ignore[return-value]

@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: uuid.UUID, request: Request) -> Response:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        if not await AdminCampaignService(session).delete(actor_id=actor.user_id, campaign_id=campaign_id): raise HTTPException(status_code=409, detail="only an existing draft can be deleted")
    return Response(status_code=204)

@router.post("/campaigns/{campaign_id}/confirm", response_model=AdminBroadcastView)
async def confirm_campaign(campaign_id: uuid.UUID, request: Request) -> AdminBroadcastView:
    actor = await owner_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminCampaignService(session).confirm(actor_id=actor.user_id, campaign_id=campaign_id)
        if row is None: raise HTTPException(status_code=409, detail="campaign cannot be confirmed")
        return row
