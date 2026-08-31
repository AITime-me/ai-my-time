"""Durable notification projection for the private operations Telegram chat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConsultationRequest, DiagnosticReport, ProfileAnswer, Touchpoint, User
from app.services.outbox import OutboundQueue


@dataclass(frozen=True)
class OpsNotification:
    event_type: str
    consultation_id: str
    text: str


class OpsNotifier(Protocol):
    async def notify(self, notification: OpsNotification) -> None: ...


class RecordingOpsNotifier:
    def __init__(self) -> None:
        self.items: list[OpsNotification] = []

    async def notify(self, notification: OpsNotification) -> None:
        self.items.append(notification)


class OpsNotificationService:
    """Projects a created consultation into the durable outbox exactly once."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = OutboundQueue(session)

    async def enqueue_created_consultation(self, request: ConsultationRequest) -> None:
        user = await self._session.get(User, request.user_id)
        if user is None:
            return
        touchpoint = await self._session.scalar(
            select(Touchpoint)
            .where(Touchpoint.user_id == user.id)
            .order_by(desc(Touchpoint.observed_at))
            .limit(1)
        )
        segment = await self._session.scalar(
            select(ProfileAnswer.answer_json)
            .where(ProfileAnswer.user_id == user.id, ProfileAnswer.question_code == "business_type")
            .order_by(desc(ProfileAnswer.revision))
            .limit(1)
        )
        report = await self._session.scalar(
            select(DiagnosticReport).where(
                DiagnosticReport.diagnostic_session_id == request.diagnostic_session_id
            )
        )
        event_type = "repeat_task" if request.origin_type == "repeat_task" else "primary_consultation"
        notification = OpsNotification(
            event_type=event_type,
            consultation_id=str(request.id),
            text=_render(
                event_type=event_type,
                user=user,
                source=touchpoint.source_code if touchpoint else None,
                campaign=_campaign(touchpoint.metadata_json) if touchpoint else None,
                segment=_answer_value(segment),
                summary=report.summary if report else None,
                repeat_task_text=request.repeat_task_text,
            ),
        )
        await self._outbox.enqueue(
            user_id=user.id,
            channel="telegram_ops",
            payload={"kind": "message", "text": notification.text},
            dedupe_key=f"ops:consultation-created:{request.id}",
        )


def _answer_value(answer: object) -> str | None:
    if isinstance(answer, dict):
        answer = answer.get("value")
    if answer is None:
        return None
    value = str(answer).strip()
    return value or None


def _campaign(metadata: dict[str, object]) -> str | None:
    value = metadata.get("campaign")
    return str(value).strip() if value is not None and str(value).strip() else None


def _render(
    *,
    event_type: str,
    user: User,
    source: str | None,
    campaign: str | None,
    segment: str | None,
    summary: str | None,
    repeat_task_text: str | None,
) -> str:
    person = user.display_name or user.telegram_first_name or "Без имени"
    telegram = f"@{user.telegram_username.lstrip('@')}" if user.telegram_username else "не указан"
    lines = [
        "Новая консультация AI My Time",
        f"Клиент: {person} · Telegram: {telegram}",
        f"Тип обращения: {'Повторное обращение — новая задача' if event_type == 'repeat_task' else 'Первичное обращение после диагностики'}",
    ]
    if source:
        lines.append(f"Источник: {source}")
    if campaign:
        lines.append(f"Кампания: {campaign}")
    if segment:
        lines.append(f"Сегмент бизнеса: {segment}")
    if event_type == "repeat_task":
        if repeat_task_text:
            lines.append(f"Задача: {repeat_task_text}")
    elif summary:
        lines.append(f"Краткий итог диагностики: {summary}")
    return "\n".join(lines)
