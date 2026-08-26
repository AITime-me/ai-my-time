"""Local-only Admin authentication primitives; no HTTP route is mounted yet."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminSession, AdminUser
from app.schemas.admin_auth import AdminActor, AdminSessionResult

_PASSWORD_MIN_LENGTH = 12
_SESSION_TTL = timedelta(hours=8)


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_password(password: str) -> str:
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError("password must be at least 12 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived).decode("ascii"),
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, raw_salt, raw_hash = encoded.split("$")
        if algorithm != "scrypt":
            return False
        expected = base64.urlsafe_b64decode(raw_hash.encode("ascii"))
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.urlsafe_b64decode(raw_salt.encode("ascii")),
            n=int(n), r=int(r), p=int(p),
        )
        return hmac.compare_digest(derived, expected)
    except (TypeError, ValueError):
        return False


class AdminAuthService:
    """Database-backed owner/manager sessions without storing raw secrets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bootstrap_owner(self, *, email: str, password: str) -> AdminActor:
        if await self._session.scalar(select(AdminUser.id).limit(1)) is not None:
            raise ValueError("admin bootstrap is already complete")
        user = AdminUser(
            email=_normalize_email(email), password_hash=_hash_password(password), role="owner"
        )
        self._session.add(user)
        await self._session.flush()
        return AdminActor(user_id=user.id, email=user.email, role=user.role)

    async def login(self, *, email: str, password: str) -> AdminSessionResult:
        user = await self._session.scalar(
            select(AdminUser).where(AdminUser.email == _normalize_email(email))
        )
        if user is None or not user.is_active or not _verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        self._session.add(
            AdminSession(
                admin_user_id=user.id,
                token_hash=_token_digest(token),
                expires_at=now + _SESSION_TTL,
            )
        )
        await self._session.flush()
        return AdminSessionResult(
            actor=AdminActor(user_id=user.id, email=user.email, role=user.role),
            session_token=token,
        )

    async def authenticate(self, *, session_token: str) -> AdminActor:
        session = await self._session.scalar(
            select(AdminSession).where(AdminSession.token_hash == _token_digest(session_token))
        )
        now = datetime.now(timezone.utc)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise ValueError("invalid session")
        user = await self._session.get(AdminUser, session.admin_user_id)
        if user is None or not user.is_active:
            raise ValueError("invalid session")
        return AdminActor(user_id=user.id, email=user.email, role=user.role)
