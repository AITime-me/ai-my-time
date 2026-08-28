"""Consent is separate from Telegram delivery reachability and lead history."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, User
from app.services.outbox import OutboundQueue

_UNSUBSCRIBED = "Вы отписались от исходящих сообщений AI My Time. Бот по-прежнему отвечает на ваши обращения. Чтобы снова получать сообщения, отправьте /subscribe."
_SUBSCRIBED = "Подписка на сообщения AI My Time снова включена."


class CommunicationConsentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)

    async def set_status(self, *, user_id: uuid.UUID, status: str) -> bool:
        if status not in {"subscribed", "unsubscribed"}:
            raise ValueError("unsupported communication status")
        user = await self._session.get(User, user_id)
        if user is None:
            return False
        if user.communication_status == status:
            return True
        user.communication_status = status
        self._session.add(Event(user_id=user_id, kind=f"communication_{status}", payload_json={}))
        await self._outbox.enqueue(
            user_id=user_id,
            channel="telegram_lead",
            payload={
                "kind": "message",
                "text": _UNSUBSCRIBED if status == "unsubscribed" else _SUBSCRIBED,
                "buttons": [],
            },
            dedupe_key=f"communication:{user_id}:{status}",
        )
        return True
