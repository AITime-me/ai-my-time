"""Real PostgreSQL proof for the first conference path.

Run only with AI_MY_TIME_TEST_DATABASE_URL pointing at an explicitly named
disposable test database. The test truncates its own tables before use.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory, session_scope
from app.models import DiagnosticSession
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.profile import ProfileService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_qr_profile_diagnostic_flow_is_durable_and_idempotent() -> None:
    asyncio.run(_run_flow(_test_database_url()))


async def _run_flow(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    try:
        async with session_scope(session_factory) as session:
            await session.execute(
                text(
                    "TRUNCATE TABLE diagnostic_reports, diagnostic_sessions, profile_answers, "
                    "business_profiles, conference_entries, events, touchpoints, "
                    "user_identities, users RESTART IDENTITY CASCADE"
                )
            )

        async with session_scope(session_factory) as session:
            first_entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(
                    telegram_user_id="900001",
                    qr_code="conference-main",
                    entry_code="qr_conf_main",
                )
            )
            assert first_entry.created_user is True
            assert first_entry.created_entry is True
            assert first_entry.next_stage == "profiling"

        async with session_scope(session_factory) as session:
            duplicate_entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(
                    telegram_user_id="900001",
                    qr_code="conference-main",
                    entry_code="qr_conf_main",
                )
            )
            assert duplicate_entry.user_id == first_entry.user_id
            assert duplicate_entry.conference_entry_id == first_entry.conference_entry_id
            assert duplicate_entry.created_user is False
            assert duplicate_entry.created_entry is False

        async with session_scope(session_factory) as session:
            profile_result = await ProfileService(session).save(
                SaveProfileAnswersCommand(
                    user_id=first_entry.user_id,
                    complete=True,
                    answers=[
                        {"question_code": "business_type", "value": "Автосервис"},
                        {"question_code": "team_size", "value": "7"},
                        {"question_code": "client_flow", "value": "Звонки и Telegram"},
                        {"question_code": "current_tools", "value": "Таблица и чат"},
                        {"question_code": "primary_pain", "value": "Теряются заявки"},
                        {"question_code": "automation_goal", "value": "Видеть следующий шаг"},
                    ],
                )
            )
            assert profile_result.profile_status == "completed"
            assert profile_result.saved_answers == 6

        async with session_scope(session_factory) as session:
            diagnostic_result = await DiagnosticPreparationService(session).prepare(
                PrepareDiagnosticCommand(user_id=first_entry.user_id)
            )
            diagnostic = await session.get(DiagnosticSession, diagnostic_result.diagnostic_session_id)
            assert diagnostic is not None
            assert diagnostic.status == "prepared"
            assert len(diagnostic.input_snapshot_json["profile_answers"]) == 6
    finally:
        try:
            async with session_scope(session_factory) as session:
                await session.execute(
                    text(
                        "TRUNCATE TABLE diagnostic_reports, diagnostic_sessions, profile_answers, "
                        "business_profiles, conference_entries, events, touchpoints, "
                        "user_identities, users RESTART IDENTITY CASCADE"
                    )
                )
        finally:
            engine = session_factory.kw["bind"]
            await engine.dispose()
