import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import AdminAuditEvent, AssistantChannelBinding, AssistantConversation, AssistantProfile, AssistantProfileVersion, AssistantRun, IntakeRequest
from app.schemas.assistant import AssistantBindingUpdate, AssistantConversationView, AssistantProfileDraft, IntakeView

router = APIRouter(prefix="/admin/assistant", tags=["admin-assistant"])


@router.get("/profiles")
async def profiles(request: Request):
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        rows = (await session.scalars(select(AssistantProfile).order_by(AssistantProfile.key))).all()
        return [{"id": str(x.id), "key": x.key, "title": x.title, "published_version_id": str(x.published_version_id) if x.published_version_id else None} for x in rows]


@router.post("/profiles/drafts", status_code=201)
async def profile_draft(payload: AssistantProfileDraft, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        profile = await session.scalar(select(AssistantProfile).where(AssistantProfile.key == payload.key).with_for_update())
        if profile is None:
            profile = AssistantProfile(key=payload.key, title=payload.title); session.add(profile); await session.flush()
        else: profile.title = payload.title
        version = int(await session.scalar(select(func.coalesce(func.max(AssistantProfileVersion.version), 0)).where(AssistantProfileVersion.profile_id == profile.id)) or 0) + 1
        row = AssistantProfileVersion(profile_id=profile.id, version=version, config_json=payload.config_json, created_by_actor_id=actor.user_id)
        session.add(row); session.add(AdminAuditEvent(actor_id=actor.user_id, action="assistant.profile_draft_created", object_type="assistant_profile_version", object_id=row.id, delta_json={"profile_id": str(profile.id), "version": version})); await session.flush()
        return {"profile_id": str(profile.id), "version_id": str(row.id), "version": row.version, "status": row.status}


@router.post("/profiles/versions/{version_id}/publish")
async def publish_profile(version_id: uuid.UUID, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        row = await session.get(AssistantProfileVersion, version_id, with_for_update=True)
        if row is None: raise HTTPException(status_code=404, detail="assistant profile version not found")
        profile = await session.get(AssistantProfile, row.profile_id, with_for_update=True); assert profile is not None
        if profile.published_version_id and profile.published_version_id != row.id:
            old = await session.get(AssistantProfileVersion, profile.published_version_id, with_for_update=True)
            if old: old.status = "superseded"
        row.status = "published"; profile.published_version_id = row.id
        session.add(AdminAuditEvent(actor_id=actor.user_id, action="assistant.profile_published", object_type="assistant_profile_version", object_id=row.id, delta_json={"profile_id": str(profile.id)}))
        return {"profile_id": str(profile.id), "version_id": str(row.id), "status": row.status}


@router.put("/bindings/{channel}")
async def binding(channel: str, payload: AssistantBindingUpdate, request: Request):
    actor = await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        profile = await session.get(AssistantProfile, payload.profile_id)
        if profile is None or (payload.is_active and profile.published_version_id is None): raise HTTPException(status_code=422, detail="assistant profile is not publishable")
        row = await session.scalar(select(AssistantChannelBinding).where(AssistantChannelBinding.channel == channel).with_for_update())
        if row is None: row = AssistantChannelBinding(channel=channel, profile_id=payload.profile_id, is_active=payload.is_active, settings_json=payload.settings_json); session.add(row)
        else: row.profile_id, row.is_active, row.settings_json = payload.profile_id, payload.is_active, payload.settings_json
        session.add(AdminAuditEvent(actor_id=actor.user_id, action="assistant.channel_binding_saved", object_type="assistant_channel_binding", object_id=row.id, delta_json={"channel": channel, "active": payload.is_active})); await session.flush()
        return {"id": str(row.id), "channel": row.channel, "profile_id": str(row.profile_id), "is_active": row.is_active, "settings_json": row.settings_json}


@router.get("/conversations", response_model=list[AssistantConversationView])
async def conversations(request: Request, limit: int = 50):
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return list((await session.scalars(select(AssistantConversation).order_by(AssistantConversation.created_at.desc()).limit(min(max(limit, 1), 100)))).all())


@router.get("/runs")
async def runs(request: Request, limit: int = 50):
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        rows = (await session.scalars(select(AssistantRun).order_by(AssistantRun.created_at.desc()).limit(min(max(limit, 1), 100)))).all()
        return [{"id": str(x.id), "conversation_id": str(x.conversation_id), "profile_version_id": str(x.profile_version_id), "status": x.status, "outcome": x.outcome, "latency_ms": x.latency_ms, "created_at": x.created_at} for x in rows]


@router.get("/intakes", response_model=list[IntakeView])
async def intakes(request: Request, limit: int = 50):
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return list((await session.scalars(select(IntakeRequest).order_by(IntakeRequest.created_at.desc()).limit(min(max(limit, 1), 100)))).all())
