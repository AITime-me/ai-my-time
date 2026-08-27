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
from app.models import DiagnosticReport, DiagnosticSession
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.diagnostic_report import RecordDiagnosticReportCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.admin_read import AdminLeadReadService
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.diagnostic_report import DiagnosticReportService
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
                        {"question_code": "business_type", "value": "Услуги"},
                        {"question_code": "team_size", "value": "7"},
                        {"question_code": "client_flow", "value": "Мессенджеры"},
                        {"question_code": "current_tools", "value": "В таблицах"},
                        {"question_code": "primary_pain", "value": "Заявки"},
                        {"question_code": "automation_goal", "value": "Не забывать вернуться к клиенту"},
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

        report_command = RecordDiagnosticReportCommand(
            diagnostic_session_id=diagnostic_result.diagnostic_session_id,
            summary="Нужно сделать следующий шаг по заявке видимым для команды.",
            priorities=[
                {
                    "title": "Статус новой заявки",
                    "reason": "Следующий ответственный не зафиксирован",
                    "confidence": "high",
                }
            ],
            next_steps=[
                {
                    "title": "Единая очередь",
                    "action": "Зафиксировать единый вход и обязательный следующий шаг",
                }
            ],
            limitations=["Результат основан на ответах анкеты."],
        )
        async with session_scope(session_factory) as session:
            report_result = await DiagnosticReportService(session).record(report_command)
            assert report_result.created is True
            assert report_result.status == "ready"
            report = await session.get(DiagnosticReport, report_result.report_id)
            assert report is not None
            assert report.priorities_json[0]["confidence"] == "high"

        async with session_scope(session_factory) as session:
            duplicate_report = await DiagnosticReportService(session).record(report_command)
            assert duplicate_report.created is False
            assert duplicate_report.report_id == report_result.report_id

        async with session_scope(session_factory) as session:
            admin_list = await AdminLeadReadService(session).list_recent()
            assert len(admin_list.items) == 1
            assert admin_list.items[0].user_id == first_entry.user_id
            assert admin_list.items[0].lifecycle_stage == "diagnostic_ready"
            assert admin_list.items[0].conference_code == "conference_2026"
            assert admin_list.items[0].diagnostic_status == "ready"
            assert admin_list.items[0].diagnostic_summary == report_command.summary
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
