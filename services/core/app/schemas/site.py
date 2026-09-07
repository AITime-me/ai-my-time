from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SiteSettingsPayload(BaseModel):
    site_title: str = Field(min_length=1, max_length=256)
    site_description: str = Field(default="", max_length=10_000)
    og_image: str | None = Field(default=None, max_length=1024)
    contacts_json: dict[str, object] = Field(default_factory=dict)
    social_links_json: dict[str, object] = Field(default_factory=dict)
    cta_json: dict[str, object] = Field(default_factory=dict)
    analytics_json: dict[str, object] = Field(default_factory=dict)


class SiteServicePayload(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=256)
    h1: str | None = Field(default=None, max_length=256)
    seo_title: str | None = Field(default=None, max_length=256)
    seo_description: str | None = Field(default=None, max_length=10_000)
    short_description: str | None = Field(default=None, max_length=10_000)
    full_description: str | None = Field(default=None, max_length=20_000)
    audience: str | None = Field(default=None, max_length=10_000)
    includes: str | None = Field(default=None, max_length=10_000)
    result: str | None = Field(default=None, max_length=10_000)
    cta_text: str | None = Field(default=None, max_length=160)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = False


class SiteCasePayload(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    category: str | None = Field(default=None, max_length=160)
    status: str | None = Field(default=None, max_length=80)
    task: str | None = Field(default=None, max_length=20_000)
    solution: str | None = Field(default=None, max_length=20_000)
    result: str | None = Field(default=None, max_length=20_000)
    note: str | None = Field(default=None, max_length=10_000)
    image_url: str | None = Field(default=None, max_length=1024)
    seo_title: str | None = Field(default=None, max_length=256)
    seo_description: str | None = Field(default=None, max_length=10_000)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = False


class SiteFaqPayload(BaseModel):
    question: str = Field(min_length=1, max_length=10_000)
    answer: str = Field(min_length=1, max_length=20_000)
    category: str | None = Field(default=None, max_length=160)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = False


class SiteLegalDraftPayload(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=50_000)


class SiteItemView(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
