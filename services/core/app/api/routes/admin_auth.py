from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.admin_auth import AdminActor
from app.services.admin_auth import AdminAuthService

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

_COOKIE_NAME = "ai_my_time_admin_session"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


def _cookie_is_secure(request: Request) -> bool:
    return request.app.state.settings.app_env == "production"


@router.post("/login", response_model=AdminActor)
async def login(payload: LoginRequest, request: Request, response: Response) -> AdminActor:
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            result = await AdminAuthService(session).login(
                email=payload.email, password=payload.password
            )
        except ValueError:
            raise HTTPException(status_code=401, detail="invalid credentials") from None
    response.set_cookie(
        key=_COOKIE_NAME,
        value=result.session_token,
        httponly=True,
        secure=_cookie_is_secure(request),
        samesite="strict",
        path="/",
        max_age=8 * 60 * 60,
    )
    return result.actor


@router.get("/me", response_model=AdminActor)
async def current_actor(request: Request) -> AdminActor:
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            return await AdminAuthService(session).authenticate(session_token=token)
        except ValueError:
            raise HTTPException(status_code=401, detail="unauthorized") from None


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> Response:
    origin = request.headers.get("origin")
    expected_origin = str(request.base_url).rstrip("/")
    if origin != expected_origin:
        raise HTTPException(status_code=403, detail="origin check failed")
    token = request.cookies.get(_COOKIE_NAME)
    if token:
        factory = get_session_factory(request)
        async with session_scope(factory) as session:
            await AdminAuthService(session).logout(session_token=token)
    response.delete_cookie(key=_COOKIE_NAME, path="/")
    response.status_code = 204
    return response
