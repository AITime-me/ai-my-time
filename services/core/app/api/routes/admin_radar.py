"""Headless Admin API for Demand Radar configuration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.api.admin_origin import require_trusted_admin_origin
from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.radar_admin import (
    RadarDestinationCreate,
    RadarDestinationList,
    RadarDestinationView,
    RadarProfileActivate,
    RadarProfileCreate,
    RadarProfileList,
    RadarProfileVersionCreate,
    RadarProfileVersionView,
    RadarProfileView,
    RadarReaderList,
    RadarSourceCreate,
    RadarSourceList,
    RadarSourcePatch,
    RadarSourceView,
)
from app.services.radar_config import RadarConfigError, RadarConfigService

router = APIRouter(prefix="/admin/radar", tags=["admin-radar"])

_TENANT_HEADER = "X-Radar-Tenant-Id"


def _map_error(error: RadarConfigError) -> HTTPException:
    if error.code in {"tenant_forbidden", "source_not_found", "profile_not_found", "version_not_found", "reader_not_found", "destination_not_found", "manifest_unavailable"}:
        status = 404 if error.code != "tenant_forbidden" else 404
        # tenant_forbidden also 404 to avoid membership enumeration
        return HTTPException(status_code=status, detail=error.message)
    if error.code in {"source_conflict", "destination_conflict", "rule_conflict", "binding_conflict", "source_version_conflict"}:
        return HTTPException(status_code=409, detail=error.code if error.code == "source_version_conflict" else error.message)
    return HTTPException(status_code=422, detail=error.message)


async def _radar_context(
    request: Request, tenant_id_header: str | None
) -> tuple[uuid.UUID, uuid.UUID]:
    actor = await current_actor(request)
    if not tenant_id_header:
        raise HTTPException(status_code=404, detail="radar tenant not found")
    try:
        tenant_id = uuid.UUID(tenant_id_header)
    except ValueError:
        raise HTTPException(status_code=404, detail="radar tenant not found") from None
    async with session_scope(get_session_factory(request)) as session:
        try:
            await RadarConfigService(session).require_tenant_membership(
                actor_id=actor.user_id, tenant_id=tenant_id
            )
        except RadarConfigError as error:
            raise _map_error(error) from None
    return actor.user_id, tenant_id


@router.get("/sources", response_model=RadarSourceList)
async def list_sources(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarSourceList:
    _, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        items = await RadarConfigService(session).list_sources(
            tenant_id=tenant_id, limit=limit, offset=offset
        )
    return RadarSourceList(items=items, limit=limit, offset=offset)


@router.post("/sources", response_model=RadarSourceView, status_code=201)
async def create_source(
    payload: RadarSourceCreate,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarSourceView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).create_source(
                actor_id=actor_id, tenant_id=tenant_id, payload=payload
            )
        except RadarConfigError as error:
            raise _map_error(error) from None


@router.patch("/sources/{source_id}", response_model=RadarSourceView)
async def patch_source(
    source_id: uuid.UUID,
    payload: RadarSourcePatch,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarSourceView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).patch_source(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_id=source_id,
                payload=payload,
            )
        except RadarConfigError as error:
            raise _map_error(error) from None


@router.get("/readers", response_model=RadarReaderList)
async def list_readers(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarReaderList:
    _, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        items = await RadarConfigService(session).list_readers(
            tenant_id=tenant_id, limit=limit, offset=offset
        )
    return RadarReaderList(items=items, limit=limit, offset=offset)


@router.get("/destinations", response_model=RadarDestinationList)
async def list_destinations(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarDestinationList:
    _, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        items = await RadarConfigService(session).list_destinations(
            tenant_id=tenant_id, limit=limit, offset=offset
        )
    return RadarDestinationList(items=items, limit=limit, offset=offset)


@router.post("/destinations", response_model=RadarDestinationView, status_code=201)
async def create_destination(
    payload: RadarDestinationCreate,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarDestinationView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).create_destination(
                actor_id=actor_id, tenant_id=tenant_id, payload=payload
            )
        except RadarConfigError as error:
            raise _map_error(error) from None


@router.get("/profiles", response_model=RadarProfileList)
async def list_profiles(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarProfileList:
    _, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        items = await RadarConfigService(session).list_profiles(
            tenant_id=tenant_id, limit=limit, offset=offset
        )
    return RadarProfileList(items=items, limit=limit, offset=offset)


@router.post("/profiles", response_model=RadarProfileView, status_code=201)
async def create_profile(
    payload: RadarProfileCreate,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarProfileView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).create_profile(
                actor_id=actor_id, tenant_id=tenant_id, payload=payload
            )
        except RadarConfigError as error:
            raise _map_error(error) from None


@router.post(
    "/profiles/{profile_id}/versions",
    response_model=RadarProfileVersionView,
    status_code=201,
)
async def create_profile_version(
    profile_id: uuid.UUID,
    payload: RadarProfileVersionCreate,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarProfileVersionView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).create_profile_version(
                actor_id=actor_id,
                tenant_id=tenant_id,
                profile_id=profile_id,
                payload=payload,
            )
        except RadarConfigError as error:
            raise _map_error(error) from None


@router.post("/profiles/{profile_id}/activate", response_model=RadarProfileView)
async def activate_profile(
    profile_id: uuid.UUID,
    payload: RadarProfileActivate,
    request: Request,
    x_radar_tenant_id: str | None = Header(default=None, alias=_TENANT_HEADER),
) -> RadarProfileView:
    require_trusted_admin_origin(request, require_json=True)
    actor_id, tenant_id = await _radar_context(request, x_radar_tenant_id)
    async with session_scope(get_session_factory(request)) as session:
        try:
            return await RadarConfigService(session).activate_profile_version(
                actor_id=actor_id,
                tenant_id=tenant_id,
                profile_id=profile_id,
                payload=payload,
            )
        except RadarConfigError as error:
            raise _map_error(error) from None
