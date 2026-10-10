"""Reusable trusted-Origin guard for Admin browser mutations."""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, Request

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _normalize_origin(value: str) -> str | None:
    raw = value.strip()
    if not raw or raw.lower() == "null":
        return None
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.path not in {"", "/"} or parts.query or parts.fragment or parts.username or parts.password:
        return None
    host = parts.hostname.lower()
    port = parts.port
    if port is None:
        return f"{parts.scheme}://{host}"
    return f"{parts.scheme}://{host}:{port}"


def require_trusted_admin_origin(request: Request, *, require_json: bool = False) -> None:
    """Reject mutating Admin requests whose Origin is not the configured trusted origin."""

    if request.method not in _MUTATING:
        return
    trusted_raw = getattr(request.app.state.settings, "admin_trusted_origin", None)
    if not trusted_raw or not str(trusted_raw).strip():
        raise HTTPException(status_code=503, detail="admin origin is not configured")
    trusted = _normalize_origin(str(trusted_raw))
    if trusted is None:
        raise HTTPException(status_code=503, detail="admin origin is not configured")

    origin_header = request.headers.get("origin")
    if origin_header is None:
        raise HTTPException(status_code=403, detail="origin check failed")
    origin = _normalize_origin(origin_header)
    if origin is None or origin != trusted:
        raise HTTPException(status_code=403, detail="origin check failed")

    if require_json:
        content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise HTTPException(status_code=415, detail="unsupported media type")
