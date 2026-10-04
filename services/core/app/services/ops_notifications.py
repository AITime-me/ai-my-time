"""Durable notification projection for the private operations Telegram chat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.website_sources import website_intent_label, website_source_label
from app.models import (
    ConsultationRequest,
    DiagnosticReport,
    DiagnosticSession,
    ProfileAnswer,
    Touchpoint,
    User,
)
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

    async def enqueue_website_start(self, *, user: User, touchpoint: Touchpoint) -> None:
        source = website_source_label(touchpoint.source_code)
        if source is None:
            return
        intent = _intent(touchpoint.metadata_json)
        await self._outbox.enqueue(
            user_id=user.id,
            channel="telegram_ops",
            payload={
                "kind": "message",
                "text": _render_website_start(
                    user=user,
                    source=source,
                    intent=intent,
                ),
            },
            dedupe_key=f"ops:website-start:{touchpoint.id}",
        )

    async def enqueue_website_diagnostic_completed(
        self,
        *,
        diagnostic: DiagnosticSession,
        report: DiagnosticReport,
    ) -> None:
        touchpoint = await self._session.scalar(
            select(Touchpoint)
            .where(
                Touchpoint.user_id == diagnostic.user_id,
                Touchpoint.observed_at <= diagnostic.created_at,
            )
            .order_by(desc(Touchpoint.observed_at))
            .limit(1)
        )
        if touchpoint is None:
            return
        source = website_source_label(touchpoint.source_code)
        if source is None:
            return
        user = await self._session.get(User, diagnostic.user_id)
        if user is None:
            return
        profile_answers = diagnostic.input_snapshot_json.get("profile_answers")
        answers = profile_answers if isinstance(profile_answers, dict) else {}
        await self._outbox.enqueue(
            user_id=user.id,
            channel="telegram_ops",
            payload={
                "kind": "message",
                "text": _render_website_diagnostic_completed(
                    user=user,
                    source=source,
                    intent=_intent(touchpoint.metadata_json),
                    business_type=_answer_value(answers.get("business_type")),
                    main_task=_answer_value(answers.get("automation_goal")),
                    summary=report.summary,
                ),
            },
            dedupe_key=f"ops:website-diagnostic-completed:{report.id}",
        )

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


def _intent(metadata: dict[str, object]) -> str | None:
    value = metadata.get("intent")
    return value if isinstance(value, str) and value in {"general", "radar"} else None


def _person_line(user: User) -> str:
    person = user.display_name or user.telegram_first_name or "Без имени"
    telegram = f"@{user.telegram_username.lstrip('@')}" if user.telegram_username else "не указан"
    return f"Клиент: {person} · Telegram: {telegram}"


def _render_website_start(*, user: User, source: str, intent: str | None) -> str:
    lines = [
        "Новый переход в диагностику с сайта",
        f"Источник: {source}",
        _person_line(user),
    ]
    if intent == "radar":
        lines.append(f"Интерес: {website_intent_label(intent)}")
    return "\n".join(lines)


def _render_website_diagnostic_completed(
    *,
    user: User,
    source: str,
    intent: str | None,
    business_type: str | None,
    main_task: str | None,
    summary: str,
) -> str:
    lines = [
        "Диагностика с сайта завершена",
        f"Источник: {source}",
        _person_line(user),
    ]
    if intent == "radar":
        lines.append(f"Интерес: {website_intent_label(intent)}")
    if business_type:
        lines.append(f"Тип бизнеса: {_concise(business_type, 160)}")
    if main_task:
        lines.append(f"Основная задача: {_concise(main_task, 320)}")
    lines.append(f"Краткий итог: {_concise(summary, 600)}")
    return "\n".join(lines)


def _concise(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


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
    lines = [
        "Новая консультация AI My Time",
        _person_line(user),
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
