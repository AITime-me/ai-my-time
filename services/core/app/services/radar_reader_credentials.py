"""File-backed Radar Reader credential map (credential_key_id -> secret)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path


class RadarCredentialStoreUnavailableError(RuntimeError):
    """Protected credential file is missing or unreadable."""


@dataclass(frozen=True)
class _CachedMap:
    mtime_ns: int
    mapping: dict[str, str]


class RadarReaderCredentialStore:
    """Loads JSON ``{credential_key_id: secret}`` and reloads when mtime changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: _CachedMap | None = None
        self._path: str | None = None

    def clear(self) -> None:
        with self._lock:
            self._cache = None
            self._path = None

    def lookup(self, *, path: str | None, credential_key_id: str) -> str | None:
        if not path or not path.strip():
            raise RadarCredentialStoreUnavailableError("credential store path is not configured")
        mapping = self._load(path.strip())
        return mapping.get(credential_key_id)

    def _load(self, path: str) -> dict[str, str]:
        file_path = Path(path)
        try:
            stat = file_path.stat()
        except OSError as error:
            raise RadarCredentialStoreUnavailableError("credential store unavailable") from error

        with self._lock:
            if (
                self._cache is not None
                and self._path == path
                and self._cache.mtime_ns == stat.st_mtime_ns
            ):
                return self._cache.mapping

        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RadarCredentialStoreUnavailableError("credential store unavailable") from error
        if not isinstance(raw, dict):
            raise RadarCredentialStoreUnavailableError("credential store unavailable")
        mapping: dict[str, str] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise RadarCredentialStoreUnavailableError("credential store unavailable")
            if not key or not value:
                raise RadarCredentialStoreUnavailableError("credential store unavailable")
            mapping[key] = value

        with self._lock:
            self._path = path
            self._cache = _CachedMap(mtime_ns=stat.st_mtime_ns, mapping=mapping)
            return mapping


_STORE = RadarReaderCredentialStore()


def get_radar_reader_credential_store() -> RadarReaderCredentialStore:
    return _STORE
