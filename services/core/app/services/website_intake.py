"""Durable intake for the bounded website → Telegram diagnostic handoff."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.website_sources import website_start_attribution
from app.models import Event, Touchpoint, User, UserIdentity
from app.schemas.website import WebsiteStartCommand, WebsiteStartResult
from app.services.ops_notifications import OpsNotificationService

_TELEGRAM_PROVIDER = "telegram"
_LEAD_BOT_SCOPE = "ai_my_time_lead_bot"
_WEBSITE_START_EVENT_NAMESPACE = uuid.UUID("60a8c79f-72e1-4cb0-86f6-a671e4cd6955")


class WebsiteIntakeService:
    """Create one website touchpoint per unique Telegram start interaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, command: WebsiteStartCommand) -> WebsiteStartResult:
        attribution = website_start_attribution(command.entry_code)
        if attribution is None:
            raise ValueError("unsupported website start payload")

        identity = await self._session.scalar(
            select(UserIdentity).where(
                UserIdentity.provider == _TELEGRAM_PROVIDER,
                UserIdentity.connection_scope == _LEAD_BOT_SCOPE,
                UserIdentity.external_id == command.telegram_user_id,
            )
        )
        created_user = identity is None
        if identity is None:
            user = User(lifecycle_stage="profiling")
            self._session.add(user)
            await self._session.flush()
            identity = UserIdentity(
                user_id=user.id,
                provider=_TELEGRAM_PROVIDER,
                connection_scope=_LEAD_BOT_SCOPE,
                external_id=command.telegram_user_id,
            )
            self._session.add(identity)
            await self._session.flush()
        else:
            user = await self._session.get(User, identity.user_id)
            if user is None:
                raise RuntimeError("identity refers to a missing user")
            if user.lifecycle_stage == "new":
                user.lifecycle_stage = "profiling"

        _apply_telegram_profile(user, command)

        marker_id = _website_start_marker_id(
            telegram_user_id=command.telegram_user_id,
            interaction_id=command.interaction_id,
        )
        marker_statement = (
            insert(Event)
            .values(
                id=marker_id,
                user_id=user.id,
                kind="website_start_received",
                payload_json={
                    "entry_code": command.entry_code,
                    "source_code": attribution.source_code,
                    "intent": attribution.intent,
                    "interaction_id": command.interaction_id,
                },
            )
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(Event.id)
        )
        created_marker_id = await self._session.scalar(marker_statement)
        if created_marker_id is None:
            return WebsiteStartResult(
                user_id=user.id,
                created_user=created_user,
                created_touchpoint=False,
                next_stage=user.lifecycle_stage,
            )

        touchpoint = Touchpoint(
            user_id=user.id,
            source_code=attribution.source_code,
            entry_code=command.entry_code,
            metadata_json={
                "intent": attribution.intent,
                "interaction_id": command.interaction_id,
            },
        )
        self._session.add(touchpoint)
        await self._session.flush()
        await OpsNotificationService(self._session).enqueue_website_start(
            user=user,
            touchpoint=touchpoint,
        )
        return WebsiteStartResult(
            user_id=user.id,
            touchpoint_id=touchpoint.id,
            created_user=created_user,
            created_touchpoint=True,
            next_stage=user.lifecycle_stage,
        )


def _website_start_marker_id(*, telegram_user_id: str, interaction_id: str) -> uuid.UUID:
    """Scope Telegram's message-id fallback to its stable private-chat identity."""

    return uuid.uuid5(
        _WEBSITE_START_EVENT_NAMESPACE,
        f"telegram-user:{telegram_user_id}:{interaction_id}",
    )


def _apply_telegram_profile(user: User, command: WebsiteStartCommand) -> None:
    user.telegram_first_name = command.telegram_first_name
    user.telegram_last_name = command.telegram_last_name
    user.telegram_username = command.telegram_username
    display_name = " ".join(
        part.strip()
        for part in (command.telegram_first_name or "", command.telegram_last_name or "")
        if part.strip()
    )
    if display_name:
        user.display_name = display_name
