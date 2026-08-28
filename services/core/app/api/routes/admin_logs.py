import uuid

from fastapi import APIRouter, Query, Request

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminOperationalTrace
from app.services.admin_trace import AdminTraceReadService

router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])


@router.get("/people/{user_id}", response_model=AdminOperationalTrace)
async def person_trace(user_id: uuid.UUID, request: Request, limit: int = Query(default=100, ge=1, le=200)) -> AdminOperationalTrace:
    await current_actor(request)
    async with session_scope(get_session_factory(request)) as session:
        return await AdminTraceReadService(session).for_person(user_id, limit=limit)
