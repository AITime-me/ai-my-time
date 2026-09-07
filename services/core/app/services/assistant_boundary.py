"""Durable, network-free Assistant boundary. It never invokes an LLM or Telegram."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AssistantChannelBinding, AssistantConversation, AssistantMessage, Event, IntakeRequest


def _digest(token: str) -> str: return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AssistantBoundaryService:
    def __init__(self, session: AsyncSession) -> None: self._session = session

    async def create_conversation(self, channel: str) -> tuple[AssistantConversation, str]:
        binding = await self._session.scalar(select(AssistantChannelBinding).where(AssistantChannelBinding.channel == channel, AssistantChannelBinding.is_active.is_(True)))
        if binding is None: raise ValueError("assistant channel is unavailable")
        token = secrets.token_urlsafe(32)
        row = AssistantConversation(channel=channel, session_key_hash=_digest(token), last_activity_at=datetime.now(timezone.utc))
        self._session.add(row); await self._session.flush()
        return row, token

    async def message(self, conversation_id: uuid.UUID, token: str, content: str) -> AssistantMessage | None:
        row = await self._session.get(AssistantConversation, conversation_id, with_for_update=True)
        if row is None or row.status != "open" or not secrets.compare_digest(row.session_key_hash, _digest(token)): return None
        message = AssistantMessage(conversation_id=row.id, actor="visitor", content=content)
        row.last_activity_at = datetime.now(timezone.utc)
        self._session.add(message); await self._session.flush()
        return message

    async def intake(self, conversation_id: uuid.UUID, token: str, *, kind: str, summary: str | None, details_json: dict[str, object], consent_record_id: uuid.UUID | None) -> IntakeRequest | None:
        conversation = await self._session.get(AssistantConversation, conversation_id, with_for_update=True)
        if conversation is None or not secrets.compare_digest(conversation.session_key_hash, _digest(token)): return None
        row = IntakeRequest(user_id=conversation.user_id, assistant_conversation_id=conversation.id, consent_record_id=consent_record_id, channel=conversation.channel, kind=kind, summary=summary, details_json=details_json)
        self._session.add(row)
        if conversation.user_id:
            self._session.add(Event(user_id=conversation.user_id, kind="assistant_intake_created", payload_json={"intake_request_id": str(row.id), "channel": conversation.channel, "kind": kind}))
        await self._session.flush()
        return row
