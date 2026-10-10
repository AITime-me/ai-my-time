"""Versioned Radar Reader–Core contract assets (fixtures + JSON Schema)."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any


def _asset_root() -> Path:
    return Path(resources.files("app.radar_assets"))


def load_fixture(name: str) -> dict[str, Any]:
    path = _asset_root() / "fixtures" / "v1" / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_schema(name: str) -> dict[str, Any]:
    path = _asset_root() / "jsonschema" / "v1" / name
    return json.loads(path.read_text(encoding="utf-8"))


def list_fixture_names() -> list[str]:
    directory = _asset_root() / "fixtures" / "v1"
    return sorted(path.name for path in directory.glob("*.json"))
