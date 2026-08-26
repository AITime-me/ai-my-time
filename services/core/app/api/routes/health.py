from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    """Liveness only; readiness will be added with PostgreSQL."""

    settings = get_settings()
    return {
        "status": "ok",
        "service": "ai-my-time-core",
        "environment": settings.app_env,
        "version": settings.app_version,
    }
