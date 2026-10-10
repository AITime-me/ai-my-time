"""Internal Radar Reader endpoints (bearer auth; no Admin session)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.radar_v1 import RadarReaderManifestV1
from app.services.radar_config import RadarConfigError, RadarConfigService
from app.services.radar_reader_auth import (
    RadarReaderAuthUnavailableError,
    RadarReaderUnauthorizedError,
    authenticate_radar_reader,
)

router = APIRouter(prefix="/internal/radar/v1", tags=["internal-radar"], include_in_schema=False)


@router.get("/reader-manifest", response_model=RadarReaderManifestV1)
async def reader_manifest(request: Request) -> RadarReaderManifestV1:
    settings = request.app.state.settings
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            principal = await authenticate_radar_reader(
                session,
                authorization=request.headers.get("authorization"),
                credentials_path=settings.radar_reader_credentials_path,
            )
            return await RadarConfigService(session).build_reader_manifest(principal)
        except RadarReaderAuthUnavailableError:
            raise HTTPException(status_code=503, detail="credential store unavailable") from None
        except RadarReaderUnauthorizedError:
            raise HTTPException(status_code=401, detail="unauthorized") from None
        except RadarConfigError as error:
            if error.code == "manifest_unavailable":
                raise HTTPException(status_code=404, detail="manifest unavailable") from None
            raise HTTPException(status_code=422, detail=error.message) from None
