"""Internal Radar Reader endpoints (bearer auth; no Admin session)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.radar_v1 import RadarErrorCode, RadarErrorV1, RadarObservationAckV1, RadarReaderManifestV1
from app.schemas.radar_validation import (
    RadarPayloadTooLargeError,
    RadarUnsupportedSchemaVersionError,
    parse_observation_payload,
)
from app.services.radar_config import RadarConfigError, RadarConfigService
from app.services.radar_ingress import RadarIngressError, RadarIngressService
from app.services.radar_reader_auth import (
    RadarReaderAuthUnavailableError,
    RadarReaderUnauthorizedError,
    authenticate_radar_reader,
)

router = APIRouter(prefix="/internal/radar/v1", tags=["internal-radar"], include_in_schema=False)


def _http_error(status: int, code: RadarErrorCode, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=RadarErrorV1(code=code, message=message, http_status=status).model_dump(mode="json"),
    )


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


@router.post("/observations", response_model=RadarObservationAckV1, status_code=201)
async def accept_observation(request: Request) -> RadarObservationAckV1:
    raw = await request.body()
    try:
        observation = parse_observation_payload(raw)
    except RadarPayloadTooLargeError as error:
        raise _http_error(413, RadarErrorCode.PAYLOAD_TOO_LARGE, str(error)) from None
    except (json.JSONDecodeError, RadarUnsupportedSchemaVersionError, ValueError) as error:
        raise _http_error(422, RadarErrorCode.INVALID_CONTRACT, str(error)) from None

    settings = request.app.state.settings
    factory = get_session_factory(request)
    async with session_scope(factory) as session:
        try:
            principal = await authenticate_radar_reader(
                session,
                authorization=request.headers.get("authorization"),
                credentials_path=settings.radar_reader_credentials_path,
            )
            return await RadarIngressService(session).accept(
                principal=principal, observation=observation
            )
        except RadarReaderAuthUnavailableError:
            raise _http_error(503, RadarErrorCode.TEMPORARY_FAILURE, "credential store unavailable") from None
        except RadarReaderUnauthorizedError:
            raise _http_error(401, RadarErrorCode.CREDENTIAL_INVALID, "unauthorized") from None
        except RadarIngressError as error:
            if error.code == "idempotency_conflict":
                raise _http_error(409, RadarErrorCode.IDEMPOTENCY_CONFLICT, error.message) from None
            raise _http_error(403, RadarErrorCode.SOURCE_FORBIDDEN, error.message) from None
