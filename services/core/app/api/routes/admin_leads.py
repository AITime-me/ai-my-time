"""Cookie-protected read-only Admin lead projection."""

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.routes.admin_auth import current_actor
from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin import AdminLeadList
from app.services.admin_read import AdminLeadReadService

router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])


@router.get("", response_model=AdminLeadList)
async def list_recent_leads(
    request: Request, limit: int = Query(default=50, ge=1, le=100)
) -> AdminLeadList:
    """Return the intentionally minimal lead projection to an authenticated Admin."""
    await current_actor(request)
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            return await AdminLeadReadService(session).list_recent(limit=limit)
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid limit") from None
