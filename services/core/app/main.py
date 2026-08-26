from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
    )
    app.include_router(health_router)
    return app


app = create_app()
