"""Audited, intentionally narrow Admin state changes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditEvent, AttentionItem, ConsultationRequest, User, UserIdentity
from app.services.outbox import OutboundQueue

_CONSULTATION_STATUSES = {"new", "in_progress", "completed", "cancelled"}
_ATTENTION_STATUSES = {"new", "in_progress", "resolved"}
_MARKETING_CONSENT_STATUSES = {"unknown", "confirmed", "revoked"}


class AdminActionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_consultation_status(
        self, *, actor_id: uuid.UUID, request_id: uuid.UUID, status: str
    ) -> ConsultationRequest | None:
        if status not in _CONSULTATION_STATUSES:
            raise ValueError("unsupported consultation status")
        request = await self._session.get(ConsultationRequest, request_id)
        if request is None:
            return None
        before = request.status
        if before != status:
            request.status = status
            self._session.add(
                AdminAuditEvent(
                    actor_id=actor_id,
                    action="consultation.status_changed",
                    object_type="consultation_request",
                    object_id=request.id,
                    delta_json={"status": {"before": before, "after": status}},
                )
            )
            attention = await self._session.scalar(
                select(AttentionItem).where(AttentionItem.consultation_request_id == request.id)
            )
            if attention is not None:
                attention_before = attention.status
                attention_after = {
                    "new": "new",
                    "in_progress": "in_progress",
                    "completed": "resolved",
                    "cancelled": "resolved",
                }[status]
                if attention_before != attention_after:
                    attention.status = attention_after
                    attention.resolved_at = (
                        datetime.now(timezone.utc) if attention_after == "resolved" else None
                    )
                    self._session.add(
                        AdminAuditEvent(
                            actor_id=actor_id,
                            action="attention.status_synchronized",
                            object_type="attention_item",
                            object_id=attention.id,
                            delta_json={
                                "status": {"before": attention_before, "after": attention_after},
                                "source": "consultation",
                            },
                        )
                    )
        return request

    async def set_attention_status(
        self, *, actor_id: uuid.UUID, item_id: uuid.UUID, status: str
    ) -> AttentionItem | None:
        if status not in _ATTENTION_STATUSES:
            raise ValueError("unsupported attention status")
        item = await self._session.get(AttentionItem, item_id)
        if item is None:
            return None
        if item.consultation_request_id is not None:
            raise ValueError("consultation-linked attention is driven by consultation status")
        before = item.status
        if before != status:
            item.status = status
            item.resolved_at = datetime.now(timezone.utc) if status == "resolved" else None
            self._session.add(
                AdminAuditEvent(
                    actor_id=actor_id,
                    action="attention.status_changed",
                    object_type="attention_item",
                    object_id=item.id,
                    delta_json={"status": {"before": before, "after": status}},
                )
            )
        return item

    async def set_marketing_consent(
        self, *, actor_id: uuid.UUID, user_id: uuid.UUID, status: str
    ) -> User | None:
        if status not in _MARKETING_CONSENT_STATUSES:
            raise ValueError("unsupported marketing consent status")
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        before = user.marketing_consent_status
        if before != status:
            user.marketing_consent_status = status
            self._session.add(
                AdminAuditEvent(
                    actor_id=actor_id,
                    action="person.marketing_consent_changed",
                    object_type="person",
                    object_id=user.id,
                    delta_json={"marketing_consent_status": {"before": before, "after": status}},
                )
            )
        return user

    async def queue_telegram_message(
        self, *, actor_id: uuid.UUID, user_id: uuid.UUID, text: str
    ) -> bool:
        user = await self._session.get(User, user_id)
        telegram_user_id = await self._session.scalar(
            select(UserIdentity.external_id).where(
                UserIdentity.user_id == user_id,
                UserIdentity.provider == "telegram",
                UserIdentity.connection_scope == "ai_my_time_lead_bot",
            )
        )
        if user is None or telegram_user_id is None:
            return False
        message = await OutboundQueue(self._session).enqueue(
            user_id=user_id,
            channel="telegram_lead",
            payload={"kind": "message", "text": text.strip(), "buttons": []},
            dedupe_key=f"admin-direct:{uuid.uuid4()}",
        )
        self._session.add(
            AdminAuditEvent(
                actor_id=actor_id,
                action="person.telegram_message_queued",
                object_type="person",
                object_id=user.id,
                delta_json={"outbox_message_id": str(message.id)},
            )
        )
        return True
