"""Internal plain-text LLM endpoint for the website server (aimytime.ru Nitro).

It has no database, Telegram, tools or user identity. The public nginx vhost
always adds forwarding headers, so their presence means the request did not
come from the local website process and is rejected as not found.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.adapters.yandex_completion import YandexCompletionClient, YandexCompletionError
from app.schemas.consultant import ConsultantCompleteRequest, ConsultantCompleteResponse

router = APIRouter(prefix="/internal/consultant", tags=["internal"], include_in_schema=False)

AUTH_HEADER = "X-Aimytime-Consultant-Auth"
MAX_BODY_BYTES = 64 * 1024
MAX_CONCURRENT = 4
_FORWARDED_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded")
_LOG = logging.getLogger(__name__)


def _configured_secret(request: Request) -> str | None:
    settings = request.app.state.settings
    if not settings.website_consultant_enabled or not settings.website_consultant_secret_path:
        return None
    try:
        secret = Path(settings.website_consultant_secret_path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return secret or None


def _slots(request: Request) -> asyncio.Semaphore:
    slots = getattr(request.app.state, "consultant_slots", None)
    if slots is None:
        slots = asyncio.Semaphore(MAX_CONCURRENT)
        request.app.state.consultant_slots = slots
    return slots


def _client(request: Request) -> YandexCompletionClient:
    override = getattr(request.app.state, "consultant_client", None)
    return override if override is not None else YandexCompletionClient(request.app.state.settings)


@router.post("/complete", response_model=ConsultantCompleteResponse)
async def complete(request: Request) -> ConsultantCompleteResponse:
    if any(name in request.headers for name in _FORWARDED_HEADERS):
        raise HTTPException(status_code=404, detail="Not Found")
    secret = _configured_secret(request)
    if secret is None:
        raise HTTPException(status_code=503, detail="consultant is unavailable")
    supplied = request.headers.get(AUTH_HEADER, "")
    if not supplied or not hmac.compare_digest(supplied.encode("utf-8"), secret.encode("utf-8")):
        raise HTTPException(status_code=401, detail="unauthorized")

    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY_BYTES):
        raise HTTPException(status_code=413, detail="payload too large")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    try:
        payload = ConsultantCompleteRequest.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=422, detail="invalid consultant payload") from None

    slots = _slots(request)
    if slots.locked():
        raise HTTPException(status_code=429, detail="consultant is busy")
    async with slots:
        try:
            text = await _client(request).complete(
                payload.system, [(message.role, message.text) for message in payload.messages],
            )
        except YandexCompletionError as error:
            _LOG.warning("website consultant completion failed", extra={"reason": str(error)})
            raise HTTPException(status_code=502, detail="consultant is unavailable") from None
    return ConsultantCompleteResponse(text=text)
