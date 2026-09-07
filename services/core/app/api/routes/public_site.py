"""Unauthenticated, read-only website content. No Admin or Assistant state leaks."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.models import SiteCase, SiteFaq, SiteLegalDocument, SiteLegalDocumentVersion, SiteService, SiteSettings

router = APIRouter(prefix="/public/site", tags=["public-site"])


@router.get("/settings")
async def settings(request: Request) -> dict[str, object]:
    async with session_scope(get_session_factory(request)) as session:
        row = await session.get(SiteSettings, 1)
        if row is None: raise HTTPException(status_code=404, detail="site content is unavailable")
        return {"site_title": row.site_title, "site_description": row.site_description, "og_image": row.og_image, "contacts": row.contacts_json, "social_links": row.social_links_json, "cta": row.cta_json, "analytics": row.analytics_json}


@router.get("/services")
async def services(request: Request) -> list[dict[str, object]]:
    async with session_scope(get_session_factory(request)) as session:
        rows = (await session.scalars(select(SiteService).where(SiteService.is_active.is_(True)).order_by(SiteService.sort_order, SiteService.title))).all()
        return [_service(row) for row in rows]


@router.get("/services/{slug}")
async def service(slug: str, request: Request) -> dict[str, object]:
    async with session_scope(get_session_factory(request)) as session:
        row = await session.scalar(select(SiteService).where(SiteService.slug == slug, SiteService.is_active.is_(True)))
        if row is None: raise HTTPException(status_code=404, detail="service not found")
        return _service(row)


@router.get("/cases")
async def cases(request: Request) -> list[dict[str, object]]:
    async with session_scope(get_session_factory(request)) as session:
        rows = (await session.scalars(select(SiteCase).where(SiteCase.is_active.is_(True)).order_by(SiteCase.sort_order, SiteCase.title))).all()
        return [{"id": str(x.id), "title": x.title, "category": x.category, "status": x.status, "task": x.task, "solution": x.solution, "result": x.result, "note": x.note, "image_url": x.image_url, "seo_title": x.seo_title, "seo_description": x.seo_description} for x in rows]


@router.get("/faq")
async def faq(request: Request) -> list[dict[str, object]]:
    async with session_scope(get_session_factory(request)) as session:
        rows = (await session.scalars(select(SiteFaq).where(SiteFaq.is_active.is_(True)).order_by(SiteFaq.sort_order, SiteFaq.question))).all()
        return [{"id": str(x.id), "question": x.question, "answer": x.answer, "category": x.category} for x in rows]


@router.get("/legal/{key}")
async def legal(key: str, request: Request) -> dict[str, object]:
    async with session_scope(get_session_factory(request)) as session:
        document = await session.scalar(select(SiteLegalDocument).where(SiteLegalDocument.key == key))
        if document is None or document.published_version_id is None: raise HTTPException(status_code=404, detail="legal document not found")
        version = await session.get(SiteLegalDocumentVersion, document.published_version_id)
        if version is None or version.status != "published": raise HTTPException(status_code=404, detail="legal document not found")
        return {"key": document.key, "title": document.title, "content": version.content, "version": version.version, "published_at": version.published_at}


def _service(row: SiteService) -> dict[str, object]:
    return {"id": str(row.id), "slug": row.slug, "title": row.title, "h1": row.h1, "seo_title": row.seo_title, "seo_description": row.seo_description, "short_description": row.short_description, "full_description": row.full_description, "audience": row.audience, "includes": row.includes, "result": row.result, "cta_text": row.cta_text}
