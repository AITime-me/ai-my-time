"""End-to-end local proof for the bounded Diagnostic AI dialogue contract."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import func, select, text

from app.db.session import create_session_factory, session_scope
from app.models import DiagnosticReport, DiagnosticSession, DiagnosticTurn, Event, OutboundMessage, User
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.diagnostic_dialogue import DiagnosticDialogueService
from app.services.profile import ProfileService


def _url() -> str:
    value = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not value:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    return value


def test_dialogue_is_bounded_price_safe_and_cta_idempotent() -> None:
    asyncio.run(_run(_url()))


async def _run(url: str) -> None:
    factory = create_session_factory(url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
            entry = await ConferenceIntakeService(session).start(ConferenceStartCommand(telegram_user_id="901001", qr_code="qr"))
            await ProfileService(session).save(SaveProfileAnswersCommand(user_id=entry.user_id, complete=True, answers=[
                {"question_code": "business_type", "value": "Услуги"},
                {"question_code": "team_size", "value": "4–10"},
                {"question_code": "client_flow", "value": "Мессенджеры"},
                {"question_code": "current_tools", "value": "В чатах"},
                {"question_code": "primary_pain", "value": "Заявки"},
                {"question_code": "automation_goal", "value": "Не терять информацию"},
            ]))
            prepared = await DiagnosticPreparationService(session).prepare(PrepareDiagnosticCommand(user_id=entry.user_id))
            service = DiagnosticDialogueService(session)
            await service.open(diagnostic_session_id=prepared.diagnostic_session_id)
            await service.receive(user_id=entry.user_id, text="Сколько стоит автоматизация?")
            await service.receive(user_id=entry.user_id, text="Менеджер получает сообщение в чате.")
            await service.receive(user_id=entry.user_id, text="Информация теряется при передаче смене.")
        async with session_scope(factory) as session:
            diagnostic = await session.get(DiagnosticSession, prepared.diagnostic_session_id)
            assert diagnostic is not None and diagnostic.status == "diagnostic_completed"
            report = await session.scalar(select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == diagnostic.id))
            assert report is not None and report.role_split_json["automation"]
            assert await session.scalar(select(func.count()).select_from(DiagnosticTurn).where(DiagnosticTurn.diagnostic_session_id == diagnostic.id)) == 4
            assert await DiagnosticDialogueService(session).receive(user_id=entry.user_id, text="А что ещё можно сделать?")
            assert await session.scalar(select(func.count()).select_from(DiagnosticTurn).where(DiagnosticTurn.diagnostic_session_id == diagnostic.id)) == 4
            messages = (await session.scalars(select(OutboundMessage).where(OutboundMessage.user_id == entry.user_id))).all()
            assert len({message.dedupe_key for message in messages}) == len(messages)
            assert any("Стоимость автоматизации" in str(message.payload_json) for message in messages)
            service = DiagnosticDialogueService(session)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=diagnostic.id)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=diagnostic.id)
        async with session_scope(factory) as session:
            user = await session.get(User, entry.user_id)
            assert user is not None and user.lifecycle_stage == "consultation_requested"
            assert await session.scalar(select(func.count()).select_from(Event).where(Event.kind == "consultation_requested")) == 1
    finally:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await factory.kw["bind"].dispose()
