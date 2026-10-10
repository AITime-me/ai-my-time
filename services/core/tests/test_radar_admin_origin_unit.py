"""Unit proofs for trusted Admin Origin guard."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.admin_origin import require_trusted_admin_origin


def _request(*, method: str, origin: str | None, trusted: str | None, content_type: str | None = None):
    headers = {}
    if origin is not None:
        headers["origin"] = origin
    if content_type is not None:
        headers["content-type"] = content_type
    return SimpleNamespace(
        method=method,
        headers=headers,
        app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(admin_trusted_origin=trusted))),
    )


def test_get_skips_origin_guard() -> None:
    require_trusted_admin_origin(_request(method="GET", origin=None, trusted="https://admin.example"))


def test_missing_trusted_config_is_503() -> None:
    with pytest.raises(HTTPException) as error:
        require_trusted_admin_origin(
            _request(method="POST", origin="https://admin.example", trusted=None),
            require_json=True,
        )
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "null",
        "https://evil.example",
        "http://admin.example",
        "https://admin.example:8443",
        "https://admin.example.evil.com",
        "https://sub.admin.example",
        "not-a-url",
        "https://admin.example/path",
    ],
)
def test_bad_origins_rejected(origin: str | None) -> None:
    with pytest.raises(HTTPException) as error:
        require_trusted_admin_origin(
            _request(
                method="POST",
                origin=origin,
                trusted="https://admin.example",
                content_type="application/json",
            ),
            require_json=True,
        )
    assert error.value.status_code == 403


def test_trusted_origin_allows_json_mutation() -> None:
    require_trusted_admin_origin(
        _request(
            method="PATCH",
            origin="https://admin.example",
            trusted="https://admin.example",
            content_type="application/json",
        ),
        require_json=True,
    )


def test_missing_json_content_type_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        require_trusted_admin_origin(
            _request(
                method="POST",
                origin="https://admin.example",
                trusted="https://admin.example",
                content_type="text/plain",
            ),
            require_json=True,
        )
    assert error.value.status_code == 415
