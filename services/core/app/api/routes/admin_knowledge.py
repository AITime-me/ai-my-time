"""Authenticated knowledge API; publishing remains an explicit Admin action."""

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminKnowledgeAssetView, AdminKnowledgeDraftCreate, AdminKnowledgeList, AdminKnowledgeVersionView
from app.services.admin_knowledge import AdminKnowledgeService

router = APIRouter(prefix="/admin/knowledge", tags=["admin-knowledge"])


async def _list(service: AdminKnowledgeService) -> AdminKnowledgeList:
    assets = await service.list_assets()
    return AdminKnowledgeList(items=[AdminKnowledgeAssetView(
        knowledge_asset_id=asset.id, namespace=asset.namespace, key=asset.key, title=asset.title,
        published_version_id=asset.published_version_id,
        versions=[AdminKnowledgeVersionView(knowledge_version_id=v.id, version=v.version, status=v.status, content_json=v.content_json, comment=v.comment, published_at=v.published_at, created_at=v.created_at) for v in await service.versions(asset.id)],
    ) for asset in assets])


@router.get("", response_model=AdminKnowledgeList)
async def list_knowledge(request: Request) -> AdminKnowledgeList:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return await _list(AdminKnowledgeService(session))


@router.post("/drafts", response_model=AdminKnowledgeVersionView, status_code=201)
async def create_draft(payload: AdminKnowledgeDraftCreate, request: Request) -> AdminKnowledgeVersionView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        try:
            row = await AdminKnowledgeService(session).create_draft(actor_id=actor.user_id, **payload.model_dump())
        except ValueError:
            raise HTTPException(status_code=422, detail="knowledge content is not accepted") from None
        return AdminKnowledgeVersionView(knowledge_version_id=row.id, version=row.version, status=row.status, content_json=row.content_json, comment=row.comment, published_at=row.published_at, created_at=row.created_at)


@router.post("/versions/{version_id}/publish", response_model=AdminKnowledgeVersionView)
async def publish(version_id: uuid.UUID, request: Request) -> AdminKnowledgeVersionView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminKnowledgeService(session).publish(actor_id=actor.user_id, version_id=version_id)
        if row is None:
            raise HTTPException(status_code=404, detail="knowledge version not found")
        return AdminKnowledgeVersionView(knowledge_version_id=row.id, version=row.version, status=row.status, content_json=row.content_json, comment=row.comment, published_at=row.published_at, created_at=row.created_at)


@router.post("/versions/{version_id}/rollback", response_model=AdminKnowledgeVersionView)
async def rollback(version_id: uuid.UUID, request: Request) -> AdminKnowledgeVersionView:
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await AdminKnowledgeService(session).rollback(actor_id=actor.user_id, version_id=version_id)
        if row is None:
            raise HTTPException(status_code=404, detail="knowledge version not found")
        return AdminKnowledgeVersionView(knowledge_version_id=row.id, version=row.version, status=row.status, content_json=row.content_json, comment=row.comment, published_at=row.published_at, created_at=row.created_at)
