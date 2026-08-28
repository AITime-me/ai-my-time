"""Versioned, business-only knowledge content for Admin.

Prompts, guardrails and runtime contracts never enter this service: it holds
only editable business material and requires an explicit publish or rollback.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent, KnowledgeAsset, KnowledgeVersion

_EDITABLE_NAMESPACES = {"business", "faq", "offers"}
_DRAFT = "draft"
_PUBLISHED = "published"
_SUPERSEDED = "superseded"


class AdminKnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_assets(self) -> list[KnowledgeAsset]:
        return (await self._session.scalars(select(KnowledgeAsset).order_by(KnowledgeAsset.namespace, KnowledgeAsset.key))).all()

    async def versions(self, asset_id: uuid.UUID) -> list[KnowledgeVersion]:
        return (await self._session.scalars(
            select(KnowledgeVersion).where(KnowledgeVersion.asset_id == asset_id).order_by(KnowledgeVersion.version.desc())
        )).all()

    async def create_draft(
        self, *, actor_id: uuid.UUID, namespace: str, key: str, title: str, content_json: dict[str, object], comment: str | None = None
    ) -> KnowledgeVersion:
        namespace, key, title = namespace.strip().lower(), key.strip().lower(), title.strip()
        if namespace not in _EDITABLE_NAMESPACES or not key or not title:
            raise ValueError("knowledge target is not editable")
        _validate_content(content_json)
        asset = await self._session.scalar(select(KnowledgeAsset).where(KnowledgeAsset.namespace == namespace, KnowledgeAsset.key == key).with_for_update())
        if asset is None:
            asset = KnowledgeAsset(namespace=namespace, key=key, title=title)
            self._session.add(asset)
            await self._session.flush()
        else:
            asset.title = title
        next_version = int(await self._session.scalar(select(func.coalesce(func.max(KnowledgeVersion.version), 0)).where(KnowledgeVersion.asset_id == asset.id)) or 0) + 1
        draft = KnowledgeVersion(asset_id=asset.id, version=next_version, status=_DRAFT, content_json=content_json, comment=comment, created_by_actor_id=actor_id)
        self._session.add(draft)
        await self._session.flush()
        self._audit(actor_id, "knowledge.draft_created", draft.id, {"asset_id": str(asset.id), "version": next_version})
        return draft

    async def publish(self, *, actor_id: uuid.UUID, version_id: uuid.UUID) -> KnowledgeVersion | None:
        version = await self._session.get(KnowledgeVersion, version_id, with_for_update=True)
        if version is None:
            return None
        asset = await self._session.get(KnowledgeAsset, version.asset_id, with_for_update=True)
        assert asset is not None
        if version.status == _PUBLISHED and asset.published_version_id == version.id:
            return version
        previous = asset.published_version_id
        if previous:
            old = await self._session.get(KnowledgeVersion, previous, with_for_update=True)
            if old is not None and old.id != version.id:
                old.status = _SUPERSEDED
        version.status = _PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        asset.published_version_id = version.id
        self._audit(actor_id, "knowledge.published", version.id, {"asset_id": str(asset.id), "previous_version_id": str(previous) if previous else None})
        return version

    async def rollback(self, *, actor_id: uuid.UUID, version_id: uuid.UUID) -> KnowledgeVersion | None:
        version = await self._session.get(KnowledgeVersion, version_id, with_for_update=True)
        if version is None:
            return None
        asset = await self._session.get(KnowledgeAsset, version.asset_id, with_for_update=True)
        assert asset is not None
        previous = asset.published_version_id
        if previous == version.id:
            return version
        if previous:
            current = await self._session.get(KnowledgeVersion, previous, with_for_update=True)
            if current is not None:
                current.status = _SUPERSEDED
        version.status = _PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        asset.published_version_id = version.id
        self._audit(actor_id, "knowledge.rolled_back", version.id, {"asset_id": str(asset.id), "from_version_id": str(previous) if previous else None})
        return version

    def _audit(self, actor_id: uuid.UUID, action: str, object_id: uuid.UUID, delta: dict[str, object]) -> None:
        self._session.add(AdminAuditEvent(actor_id=actor_id, action=action, object_type="knowledge_version", object_id=object_id, delta_json=delta))


def _validate_content(content_json: dict[str, object]) -> None:
    if not content_json or len(str(content_json)) > 20_000:
        raise ValueError("invalid knowledge content")
