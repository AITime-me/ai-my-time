"""Core-owned website CMS writes with an immutable Admin audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent, SiteCase, SiteFaq, SiteLegalDocument, SiteLegalDocumentVersion, SiteService, SiteSettings


class AdminSiteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def settings(self) -> SiteSettings | None:
        return await self._session.get(SiteSettings, 1)

    async def save_settings(self, actor_id: uuid.UUID, payload: dict[str, Any]) -> SiteSettings:
        row = await self._session.get(SiteSettings, 1)
        if row is None:
            row = SiteSettings(id=1, **payload)
            self._session.add(row)
        else:
            for key, value in payload.items(): setattr(row, key, value)
        self._audit(actor_id, "site.settings_saved", "site_settings", None)
        await self._session.flush()
        return row

    async def list_rows(self, kind: str) -> list[object]:
        model = _model(kind)
        return (await self._session.scalars(select(model).order_by(model.created_at.desc()))).all()

    async def save_row(self, actor_id: uuid.UUID, kind: str, payload: dict[str, Any], item_id: uuid.UUID | None = None) -> object | None:
        model = _model(kind)
        row = await self._session.get(model, item_id, with_for_update=True) if item_id else None
        if item_id and row is None: return None
        if row is None:
            row = model(**payload)
            self._session.add(row)
            action = "created"
        else:
            for key, value in payload.items(): setattr(row, key, value)
            action = "updated"
        await self._session.flush()
        self._audit(actor_id, f"site.{kind}_{action}", model.__tablename__, row.id)
        return row

    async def delete_row(self, actor_id: uuid.UUID, kind: str, item_id: uuid.UUID) -> bool:
        model = _model(kind)
        row = await self._session.get(model, item_id, with_for_update=True)
        if row is None: return False
        self._audit(actor_id, f"site.{kind}_deleted", model.__tablename__, row.id)
        await self._session.delete(row)
        return True

    async def legal_draft(self, actor_id: uuid.UUID, key: str, title: str, content: str) -> SiteLegalDocumentVersion:
        key = key.strip().lower()
        document = await self._session.scalar(select(SiteLegalDocument).where(SiteLegalDocument.key == key).with_for_update())
        if document is None:
            document = SiteLegalDocument(key=key, title=title)
            self._session.add(document); await self._session.flush()
        else:
            document.title = title
        version = int(await self._session.scalar(select(func.coalesce(func.max(SiteLegalDocumentVersion.version), 0)).where(SiteLegalDocumentVersion.document_id == document.id)) or 0) + 1
        row = SiteLegalDocumentVersion(document_id=document.id, version=version, content=content, created_by_actor_id=actor_id)
        self._session.add(row); await self._session.flush()
        self._audit(actor_id, "site.legal_draft_created", "site_legal_document_version", row.id)
        return row

    async def publish_legal(self, actor_id: uuid.UUID, version_id: uuid.UUID) -> SiteLegalDocumentVersion | None:
        row = await self._session.get(SiteLegalDocumentVersion, version_id, with_for_update=True)
        if row is None: return None
        document = await self._session.get(SiteLegalDocument, row.document_id, with_for_update=True)
        assert document is not None
        if document.published_version_id and document.published_version_id != row.id:
            prior = await self._session.get(SiteLegalDocumentVersion, document.published_version_id, with_for_update=True)
            if prior: prior.status = "superseded"
        row.status = "published"; row.published_at = datetime.now(timezone.utc); document.published_version_id = row.id
        self._audit(actor_id, "site.legal_published", "site_legal_document_version", row.id)
        return row

    def _audit(self, actor_id: uuid.UUID, action: str, object_type: str, object_id: uuid.UUID | None) -> None:
        self._session.add(AdminAuditEvent(actor_id=actor_id, action=action, object_type=object_type, object_id=object_id, delta_json={}))


def _model(kind: str):
    return {"services": SiteService, "cases": SiteCase, "faq": SiteFaq}[kind]
