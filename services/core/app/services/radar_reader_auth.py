"""Authenticate Radar Reader bearer credentials against the file-backed store."""

from __future__ import annotations

import hmac
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RadarReader, RadarTenant
from app.services.radar_reader_credentials import (
    RadarCredentialStoreUnavailableError,
    RadarReaderCredentialStore,
    get_radar_reader_credential_store,
)

_BEARER_PREFIX = re.compile(r"^Bearer\s+(.+)$")


class RadarReaderUnauthorizedError(ValueError):
    """Unified auth failure (unknown/wrong/disabled) — map to HTTP 401."""


class RadarReaderAuthUnavailableError(RuntimeError):
    """Credential store unavailable — map to HTTP 503."""


@dataclass(frozen=True)
class RadarReaderPrincipal:
    reader_id: uuid.UUID
    tenant_id: uuid.UUID
    credential_key_id: str
    reader_key: str


def parse_reader_bearer(authorization: str | None) -> tuple[str, str]:
    if not authorization:
        raise RadarReaderUnauthorizedError("unauthorized")
    match = _BEARER_PREFIX.fullmatch(authorization.strip())
    if match is None:
        raise RadarReaderUnauthorizedError("unauthorized")
    token = match.group(1)
    key_id, separator, secret = token.partition(".")
    if not separator or not key_id or not secret or " " in key_id or " " in secret:
        raise RadarReaderUnauthorizedError("unauthorized")
    return key_id, secret


async def authenticate_radar_reader(
    session: AsyncSession,
    *,
    authorization: str | None,
    credentials_path: str | None,
    store: RadarReaderCredentialStore | None = None,
) -> RadarReaderPrincipal:
    key_id, secret = parse_reader_bearer(authorization)
    credential_store = store or get_radar_reader_credential_store()
    try:
        expected = credential_store.lookup(path=credentials_path, credential_key_id=key_id)
    except RadarCredentialStoreUnavailableError as error:
        raise RadarReaderAuthUnavailableError("credential store unavailable") from error
    if expected is None or not hmac.compare_digest(secret, expected):
        raise RadarReaderUnauthorizedError("unauthorized")

    reader = await session.scalar(
        select(RadarReader).where(RadarReader.credential_key_id == key_id)
    )
    if reader is None or not reader.enabled:
        raise RadarReaderUnauthorizedError("unauthorized")
    tenant = await session.get(RadarTenant, reader.tenant_id)
    if tenant is None or not tenant.enabled:
        raise RadarReaderUnauthorizedError("unauthorized")
    return RadarReaderPrincipal(
        reader_id=reader.id,
        tenant_id=reader.tenant_id,
        credential_key_id=reader.credential_key_id,
        reader_key=reader.reader_key,
    )
