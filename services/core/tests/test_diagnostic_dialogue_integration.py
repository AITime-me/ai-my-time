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
from tests.doubles import ScriptedDiagnosticProvider


def _url() -> str:
    value = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not value:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    return value


def test_dialogue_is_bounded_price_safe_and_cta_idempotent() -> None:
    asyncio.run(_run(_url()))


def test_consultation_cta_is_idempotent_per_diagnostic_result() -> None:
    asyncio.run(_run_consultation_per_result(_url()))


def test_legacy_prepared_session_is_not_converted_or_lost_without_provider() -> None:
    asyncio.run(_run_legacy_prepared(_url()))


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
            service = DiagnosticDialogueService(session, ScriptedDiagnosticProvider())
            await service.open(diagnostic_session_id=prepared.diagnostic_session_id)
            opening = await session.scalar(
                select(OutboundMessage.payload_json).where(OutboundMessage.dedupe_key == f"diagnostic:{prepared.diagnostic_session_id}:opening")
            )
            assert opening is not None and "Мессенджеры" in str(opening) and "следующий шаг" in str(opening)
            await service.receive(user_id=entry.user_id, text="Сколько стоит автоматизация?")
            await service.receive(user_id=entry.user_id, text="Менеджер получает сообщение в чате.")
            followup = await session.scalar(
                select(OutboundMessage.payload_json).where(OutboundMessage.dedupe_key == f"diagnostic:{prepared.diagnostic_session_id}:question:2")
            )
            assert followup is not None and "Менеджер получает сообщение в чате" in str(followup)
            await service.receive(user_id=entry.user_id, text="Информация теряется при передаче смене.")
        async with session_scope(factory) as session:
            diagnostic = await session.get(DiagnosticSession, prepared.diagnostic_session_id)
            assert diagnostic is not None and diagnostic.status == "diagnostic_completed"
            report = await session.scalar(select(DiagnosticReport).where(DiagnosticReport.diagnostic_session_id == diagnostic.id))
            assert report is not None and report.role_split_json["automation"]
            assert report.result_version == "v2"
            assert report.result_json["problem_types"] == ["execution_gap", "observability_gap"]
            assert await session.scalar(select(func.count()).select_from(DiagnosticTurn).where(DiagnosticTurn.diagnostic_session_id == diagnostic.id)) == 4
            assert await DiagnosticDialogueService(session, ScriptedDiagnosticProvider()).receive(user_id=entry.user_id, text="А что ещё можно сделать?")
            assert await session.scalar(select(func.count()).select_from(DiagnosticTurn).where(DiagnosticTurn.diagnostic_session_id == diagnostic.id)) == 4
            messages = (await session.scalars(select(OutboundMessage).where(OutboundMessage.user_id == entry.user_id))).all()
            assert len({message.dedupe_key for message in messages}) == len(messages)
            assert any("Стоимость автоматизации" in str(message.payload_json) for message in messages)
            result_payload = next(message.payload_json for message in messages if message.dedupe_key.endswith(":result"))
            result_text = str(result_payload["text"])
            for section in ("Что сейчас происходит", "Где теряется результат", "Как это может работать", "Что может взять на себя система", "Что останется человеку", "Что ещё важно понять"):
                assert section in result_text
            assert "execution_gap" not in result_text
            assert "role_split" not in result_text
            service = DiagnosticDialogueService(session, ScriptedDiagnosticProvider())
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


async def _run_consultation_per_result(url: str) -> None:
    factory = create_session_factory(url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
            entry = await ConferenceIntakeService(session).start(ConferenceStartCommand(telegram_user_id="901006", qr_code="qr"))
            await ProfileService(session).save(SaveProfileAnswersCommand(user_id=entry.user_id, complete=True, answers=[
                {"question_code": "business_type", "value": "Услуги"},
                {"question_code": "team_size", "value": "4–10"},
                {"question_code": "client_flow", "value": "Мессенджеры"},
                {"question_code": "current_tools", "value": "В чатах"},
                {"question_code": "primary_pain", "value": "Заявки"},
                {"question_code": "automation_goal", "value": "Не терять информацию"},
            ]))
            service = DiagnosticDialogueService(session, ScriptedDiagnosticProvider())
            first = await DiagnosticPreparationService(session).prepare(PrepareDiagnosticCommand(user_id=entry.user_id))
            await _complete_dialogue(service, entry.user_id, first.diagnostic_session_id)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=first.diagnostic_session_id)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=first.diagnostic_session_id)

            second = await DiagnosticPreparationService(session).prepare(PrepareDiagnosticCommand(user_id=entry.user_id))
            await _complete_dialogue(service, entry.user_id, second.diagnostic_session_id)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=second.diagnostic_session_id)
            assert await service.consultation_requested(user_id=entry.user_id, diagnostic_session_id=second.diagnostic_session_id)

        async with session_scope(factory) as session:
            events = (await session.scalars(
                select(Event).where(Event.kind == "consultation_requested").order_by(Event.occurred_at)
            )).all()
            assert len(events) == 2
            assert {event.payload_json["diagnostic_session_id"] for event in events} == {
                str(first.diagnostic_session_id), str(second.diagnostic_session_id)
            }
            confirmations = (await session.scalars(
                select(OutboundMessage).where(OutboundMessage.dedupe_key.like("diagnostic:%:consultation:confirmation"))
            )).all()
            assert len(confirmations) == 2
            assert len({message.dedupe_key for message in confirmations}) == 2
    finally:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await factory.kw["bind"].dispose()


async def _complete_dialogue(service: DiagnosticDialogueService, user_id, diagnostic_session_id) -> None:
    assert await service.open(diagnostic_session_id=diagnostic_session_id)
    assert await service.receive(user_id=user_id, text="Менеджер получает сообщение в чате.")
    assert await service.receive(user_id=user_id, text="Информация теряется при передаче смене.")


async def _run_legacy_prepared(url: str) -> None:
    factory = create_session_factory(url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
            entry = await ConferenceIntakeService(session).start(ConferenceStartCommand(telegram_user_id="901005", qr_code="qr"))
            await ProfileService(session).save(SaveProfileAnswersCommand(user_id=entry.user_id, complete=True, answers=[
                {"question_code": "business_type", "value": "Услуги"},
                {"question_code": "team_size", "value": "4–10"},
                {"question_code": "client_flow", "value": "Мессенджеры"},
                {"question_code": "current_tools", "value": "В чатах"},
                {"question_code": "primary_pain", "value": "Заявки"},
                {"question_code": "automation_goal", "value": "Не терять информацию"},
            ]))
            legacy = await DiagnosticPreparationService(session).prepare(PrepareDiagnosticCommand(user_id=entry.user_id))
            service = DiagnosticDialogueService(session, None)
            assert await service.receive(user_id=entry.user_id, text="Продолжим?")
            assert await service.receive(user_id=entry.user_id, text="Продолжим?")
        async with session_scope(factory) as session:
            diagnostic = await session.get(DiagnosticSession, legacy.diagnostic_session_id)
            assert diagnostic is not None and diagnostic.status == "prepared"
            assert await session.scalar(select(func.count()).select_from(DiagnosticTurn)) == 0
            assert await session.scalar(select(func.count()).select_from(OutboundMessage).where(
                OutboundMessage.dedupe_key == f"diagnostic:{legacy.diagnostic_session_id}:provider-unavailable"
            )) == 1
    finally:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await factory.kw["bind"].dispose()
