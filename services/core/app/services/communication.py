"""Consent is separate from Telegram delivery reachability and lead history."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, User
from app.services.outbox import OutboundQueue

_UNSUBSCRIBED = "Вы больше не будете получать полезные материалы AI My Time. Доступ к меню, прошлому результату, новой задаче и консультации сохранён."
_UNSUBSCRIBED_ALREADY = "Полезные материалы уже отключены. Доступ к меню, результату и консультации сохранён."
_SUBSCRIBED = "Подписка на полезные материалы AI My Time включена. Будем присылать только полезные материалы, когда они появятся."
_SUBSCRIBED_ALREADY = "Вы уже получаете полезные материалы AI My Time."


def subscription_button(user: User) -> dict[str, str]:
    subscribed = user.content_subscription_status == "subscribed"
    return {
        "text": "Не получать полезные материалы" if subscribed else "Получать полезные материалы",
        "callback_data": f"content:{'unsubscribe' if subscribed else 'subscribe'}:{user.id}",
    }


class ContentSubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)

    async def set_status(self, *, user_id: uuid.UUID, status: str, interaction_id: str) -> bool:
        if status not in {"subscribed", "unsubscribed"}:
            raise ValueError("unsupported communication status")
        user = await self._session.get(User, user_id)
        if user is None:
            return False
        changed = user.content_subscription_status != status
        if changed:
            user.content_subscription_status = status
            self._session.add(Event(user_id=user_id, kind=f"content_{status}", payload_json={}))
        await self._outbox.enqueue(
            user_id=user_id,
            channel="telegram_lead",
            payload={
                "kind": "message",
                "text": (
                    _UNSUBSCRIBED if changed else _UNSUBSCRIBED_ALREADY
                ) if status == "unsubscribed" else (
                    _SUBSCRIBED if changed else _SUBSCRIBED_ALREADY
                ),
                "buttons": [],
            },
            dedupe_key=f"content-subscription:{user_id}:{status}:{interaction_id}",
        )
        return True
