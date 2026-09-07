import uuid

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.site import SiteCasePayload, SiteFaqPayload, SiteLegalDraftPayload, SiteServicePayload, SiteSettingsPayload
from app.services.admin_site import AdminSiteService

router = APIRouter(prefix="/admin/site", tags=["admin-site"])


@router.get("/settings")
async def get_settings(request: Request):
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminSiteService(session).settings()
        if row is None: raise HTTPException(status_code=404, detail="site settings are not initialized")
        return {"id": row.id, **SiteSettingsPayload.model_validate(row, from_attributes=True).model_dump()}


@router.put("/settings")
async def save_settings(payload: SiteSettingsPayload, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminSiteService(session).save_settings(actor.user_id, payload.model_dump())
        return {"id": row.id, **SiteSettingsPayload.model_validate(row, from_attributes=True).model_dump()}


def _crud(kind: str, payload_type):
    async def list_rows(request: Request):
        await current_actor(request)
        async with session_scope(get_session_factory(request)) as session:
            return [payload_type.model_validate(x, from_attributes=True).model_dump() | {"id": str(x.id)} for x in await AdminSiteService(session).list_rows(kind)]
    async def create(payload: payload_type, request: Request):
        actor = await current_actor(request)
        async with session_scope(get_session_factory(request)) as session:
            row = await AdminSiteService(session).save_row(actor.user_id, kind, payload.model_dump())
            assert row is not None
            return payload_type.model_validate(row, from_attributes=True).model_dump() | {"id": str(row.id)}
    async def update(item_id: uuid.UUID, payload: payload_type, request: Request):
        actor = await current_actor(request)
        async with session_scope(get_session_factory(request)) as session:
            row = await AdminSiteService(session).save_row(actor.user_id, kind, payload.model_dump(), item_id)
            if row is None: raise HTTPException(status_code=404, detail="site item not found")
            return payload_type.model_validate(row, from_attributes=True).model_dump() | {"id": str(row.id)}
    async def delete(item_id: uuid.UUID, request: Request):
        actor = await current_actor(request)
        async with session_scope(get_session_factory(request)) as session:
            if not await AdminSiteService(session).delete_row(actor.user_id, kind, item_id): raise HTTPException(status_code=404, detail="site item not found")
        return Response(status_code=204)
    router.add_api_route(f"/{kind}", list_rows, methods=["GET"])
    router.add_api_route(f"/{kind}", create, methods=["POST"], status_code=201)
    router.add_api_route(f"/{kind}/{{item_id}}", update, methods=["PUT"])
    router.add_api_route(f"/{kind}/{{item_id}}", delete, methods=["DELETE"], status_code=204)


_crud("services", SiteServicePayload)
_crud("cases", SiteCasePayload)
_crud("faq", SiteFaqPayload)


@router.post("/legal/{key}/drafts", status_code=201)
async def legal_draft(key: str, payload: SiteLegalDraftPayload, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminSiteService(session).legal_draft(actor.user_id, key, payload.title, payload.content)
        return {"version_id": str(row.id), "version": row.version, "status": row.status}


@router.post("/legal/versions/{version_id}/publish")
async def publish_legal(version_id: uuid.UUID, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminSiteService(session).publish_legal(actor.user_id, version_id)
        if row is None: raise HTTPException(status_code=404, detail="legal version not found")
        return {"version_id": str(row.id), "version": row.version, "status": row.status}
