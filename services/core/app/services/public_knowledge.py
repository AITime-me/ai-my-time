"""Read-only public knowledge projection shared by the site and Assistant.

The Assistant consumes the same published website records instead of a copied
knowledge base. Runtime prompts and Diagnostic AI assets remain outside this
projection.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SiteCase, SiteFaq, SiteService


class PublicKnowledgeReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshot(self) -> dict[str, list[dict[str, object]]]:
        services = (await self._session.scalars(
            select(SiteService).where(SiteService.is_active.is_(True)).order_by(SiteService.sort_order, SiteService.title)
        )).all()
        cases = (await self._session.scalars(
            select(SiteCase).where(SiteCase.is_active.is_(True)).order_by(SiteCase.sort_order, SiteCase.title)
        )).all()
        faq = (await self._session.scalars(
            select(SiteFaq).where(SiteFaq.is_active.is_(True)).order_by(SiteFaq.sort_order, SiteFaq.question)
        )).all()
        return {
            "services": [
                {
                    "id": str(row.id), "slug": row.slug, "title": row.title,
                    "description": row.full_description or row.short_description,
                    "audience": row.audience, "includes": row.includes, "result": row.result,
                }
                for row in services
            ],
            "cases": [
                {
                    "id": str(row.id), "title": row.title, "category": row.category,
                    "task": row.task, "solution": row.solution, "result": row.result,
                }
                for row in cases
            ],
            "faq": [{"id": str(row.id), "question": row.question, "answer": row.answer} for row in faq],
        }
