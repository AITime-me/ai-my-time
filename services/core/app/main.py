from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.admin_auth import router as admin_auth_router
from app.api.routes.admin_leads import router as admin_leads_router
from app.api.routes.health import router as health_router
from app.api.routes.telegram_lead import router as telegram_lead_router
from app.core.settings import get_settings
from app.db.session import create_session_factory


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        if settings.database_url:
            app.state.session_factory = create_session_factory(settings.database_url)
        try:
            yield
        finally:
            factory = getattr(app.state, "session_factory", None)
            if factory is not None:
                await factory.kw["bind"].dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_leads_router)
    app.include_router(telegram_lead_router)
    return app


app = create_app()
