"""Real PostgreSQL proof for durable profile states and outbox de-duplication."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import func, select, text

from app.db.session import create_session_factory, session_scope
from app.models import DiagnosticSession, LeadBotSession, OutboundMessage
from app.schemas.conference import ConferenceStartCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.lead_profile_flow import LeadProfileFlow, PROFILE_STEPS
from tests.doubles import ScriptedDiagnosticProvider


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_profile_state_and_outbox_survive_retries() -> None:
    asyncio.run(_run_flow(_test_database_url()))


def test_profile_steps_match_approved_product_copy() -> None:
    assert [(step.code, step.text, step.options) for step in PROFILE_STEPS] == [
        (
            "business_type",
            "Что является основой вашего бизнеса?",
            (
                "Услуги",
                "Продажа товаров",
                "Производство",
                "Проектные / подрядные работы",
                "Смешанная модель",
                "Другое",
            ),
        ),
        ("team_size", "Сколько человек сейчас в вашей команде?", ("1–3", "4–10", "11–30", "Больше 30")),
        (
            "client_flow",
            "Откуда чаще всего приходят новые обращения?",
            ("Звонки", "Мессенджеры", "Соцсети", "Сайт", "Площадки / маркетплейсы", "Другое"),
        ),
        (
            "current_tools",
            "Где вы сейчас записываете и отслеживаете заявки?",
            (
                "В чатах",
                "В таблицах",
                "В CRM",
                "В блокноте / на бумаге",
                "В нескольких местах",
                "Нигде системно",
            ),
        ),
        ("primary_pain", "Что сейчас важнее всего перестать терять?", ("Заявки", "Время", "Деньги", "Контроль")),
        (
            "automation_goal",
            "Что хотелось бы изменить в первую очередь?",
            (
                "Быстрее отвечать клиентам",
                "Не забывать вернуться к клиенту",
                "Не терять информацию",
                "Меньше контролировать вручную",
            ),
        ),
    ]


async def _run_flow(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE outbound_messages, lead_bot_sessions, diagnostic_reports, "
                    "diagnostic_sessions, profile_answers, business_profiles, conference_entries, "
                    "events, touchpoints, user_identities, users RESTART IDENTITY CASCADE"
                )
            )
        async with session_scope(factory) as session:
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(telegram_user_id="900002", qr_code="qr_conf_main")
            )
            flow = LeadProfileFlow(session, ScriptedDiagnosticProvider())
            await flow.start(user_id=entry.user_id)
            await flow.start(user_id=entry.user_id)

        async with session_scope(factory) as session:
            flow = LeadProfileFlow(session, ScriptedDiagnosticProvider())
            for step in PROFILE_STEPS:
                result = await flow.answer(
                    user_id=entry.user_id, question_code=step.code, value=step.options[0]
                )
            assert result.status == "completed"
            assert result.state == "complete"
            flow_row = await session.scalar(
                select(LeadBotSession).where(LeadBotSession.user_id == entry.user_id)
            )
            assert flow_row is not None
            assert flow_row.version == 7
            assert await session.scalar(
                select(func.count()).select_from(OutboundMessage)
            ) == 7
            assert await session.scalar(
                select(func.count()).select_from(DiagnosticSession)
            ) == 1
    finally:
        try:
            async with session_scope(factory) as session:
                await session.execute(
                    text(
                        "TRUNCATE TABLE outbound_messages, lead_bot_sessions, diagnostic_reports, "
                        "diagnostic_sessions, profile_answers, business_profiles, conference_entries, "
                        "events, touchpoints, user_identities, users RESTART IDENTITY CASCADE"
                    )
                )
        finally:
            await factory.kw["bind"].dispose()
