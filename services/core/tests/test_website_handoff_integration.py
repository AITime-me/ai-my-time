"""PostgreSQL coverage for website → Telegram diagnostic attribution."""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import func, select, text

from app.db.session import create_session_factory, session_scope
from app.models import ConsultationRequest, OutboundMessage, Touchpoint
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.diagnostic_report import RecordDiagnosticReportCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.schemas.website import WebsiteStartCommand
from app.services.admin_read import AdminLeadReadService
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.diagnostic_report import DiagnosticReportService
from app.services.ops_notifications import OpsNotificationService
from app.services.profile import ProfileService
from app.services.website_intake import WebsiteIntakeService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


def test_website_handoff_is_attributed_notified_and_idempotent() -> None:
    asyncio.run(_run_website_handoff(_test_database_url()))


def test_fallback_message_id_is_deduplicated_per_telegram_user() -> None:
    asyncio.run(_run_fallback_message_scope(_test_database_url()))


async def _run_fallback_message_scope(database_url: str) -> None:
    factory = create_session_factory(database_url)
    user_ids = []
    try:
        await _clear(factory)
        for telegram_user_id in ("910101", "910102"):
            async with session_scope(factory) as session:
                created = await WebsiteIntakeService(session).start(
                    WebsiteStartCommand(
                        telegram_user_id=telegram_user_id,
                        entry_code="site_contacts",
                        interaction_id="telegram-message:77",
                    )
                )
                assert created.created_touchpoint is True
                user_ids.append(created.user_id)

        async with session_scope(factory) as session:
            replay = await WebsiteIntakeService(session).start(
                WebsiteStartCommand(
                    telegram_user_id="910101",
                    entry_code="site_contacts",
                    interaction_id="telegram-message:77",
                )
            )
            assert replay.created_touchpoint is False

        async with session_scope(factory) as session:
            assert await session.scalar(
                select(func.count())
                .select_from(Touchpoint)
                .where(Touchpoint.user_id.in_(user_ids))
            ) == 2
            assert await session.scalar(
                select(func.count())
                .select_from(OutboundMessage)
                .where(
                    OutboundMessage.user_id.in_(user_ids),
                    OutboundMessage.dedupe_key.like("ops:website-start:%"),
                )
            ) == 2
    finally:
        await _clear(factory)
        await factory.kw["bind"].dispose()


async def _run_website_handoff(database_url: str) -> None:
    factory = create_session_factory(database_url)
    website_user_id = None
    try:
        await _clear(factory)
        starts = (
            ("site_consultant", "website_consultant", "general"),
            ("site_contacts", "website_contacts", "general"),
            ("site_header", "website_header", "general"),
            ("site_consultant_radar", "website_consultant", "radar"),
        )
        for index, (entry_code, expected_source, expected_intent) in enumerate(starts, start=1):
            async with session_scope(factory) as session:
                result = await WebsiteIntakeService(session).start(
                    WebsiteStartCommand(
                        telegram_user_id="910001",
                        entry_code=entry_code,
                        interaction_id=f"telegram-update:{index}",
                        telegram_first_name="Анна",
                        telegram_last_name="Иванова",
                        telegram_username="anna_owner",
                    )
                )
                website_user_id = result.user_id
                assert result.created_touchpoint is True
                touchpoint = await session.get(Touchpoint, result.touchpoint_id)
                assert touchpoint is not None
                assert touchpoint.source_code == expected_source
                assert touchpoint.entry_code == entry_code
                assert touchpoint.metadata_json["intent"] == expected_intent

        assert website_user_id is not None
        async with session_scope(factory) as session:
            replay = await WebsiteIntakeService(session).start(
                WebsiteStartCommand(
                    telegram_user_id="910001",
                    entry_code="site_consultant_radar",
                    interaction_id="telegram-update:4",
                    telegram_first_name="Анна",
                    telegram_last_name="Иванова",
                    telegram_username="anna_owner",
                )
            )
            assert replay.created_user is False
            assert replay.created_touchpoint is False

        async with session_scope(factory) as session:
            assert await session.scalar(
                select(func.count()).select_from(Touchpoint).where(Touchpoint.user_id == website_user_id)
            ) == 4
            website_start_messages = (
                await session.scalars(
                    select(OutboundMessage).where(
                        OutboundMessage.dedupe_key.like("ops:website-start:%")
                    )
                )
            ).all()
            assert len(website_start_messages) == 4
            radar_text = next(
                str(message.payload_json["text"])
                for message in website_start_messages
                if "Радар спроса" in str(message.payload_json["text"])
            )
            assert "Новый переход в диагностику с сайта" in radar_text
            assert "Сайт · AI-консультант" in radar_text
            assert "Радар спроса" in radar_text
            assert "Анна Иванова" in radar_text and "@anna_owner" in radar_text
            assert "910001" not in radar_text

        async with session_scope(factory) as session:
            await ProfileService(session).save(
                SaveProfileAnswersCommand(
                    user_id=website_user_id,
                    complete=True,
                    answers=[
                        {"question_code": "business_type", "value": "Услуги"},
                        {"question_code": "team_size", "value": "4–10"},
                        {"question_code": "client_flow", "value": "Сайт"},
                        {"question_code": "current_tools", "value": "В таблицах"},
                        {"question_code": "primary_pain", "value": "Заявки"},
                        {
                            "question_code": "automation_goal",
                            "value": "Не забывать вернуться к клиенту",
                        },
                    ],
                )
            )
            prepared = await DiagnosticPreparationService(session).prepare(
                PrepareDiagnosticCommand(user_id=website_user_id)
            )

        report_command = RecordDiagnosticReportCommand(
            diagnostic_session_id=prepared.diagnostic_session_id,
            summary="Нужно сделать следующий шаг по заявке видимым для команды.",
            priorities=[
                {
                    "title": "Статус заявки",
                    "reason": "Следующий шаг не виден",
                    "confidence": "high",
                }
            ],
            next_steps=[
                {
                    "title": "Единая очередь",
                    "action": "Зафиксировать единый вход",
                }
            ],
        )
        async with session_scope(factory) as session:
            recorded = await DiagnosticReportService(session).record(report_command)
            assert recorded.created is True
        async with session_scope(factory) as session:
            duplicate = await DiagnosticReportService(session).record(report_command)
            assert duplicate.created is False

        async with session_scope(factory) as session:
            completed_messages = (
                await session.scalars(
                    select(OutboundMessage).where(
                        OutboundMessage.dedupe_key
                        == f"ops:website-diagnostic-completed:{recorded.report_id}"
                    )
                )
            ).all()
            assert len(completed_messages) == 1
            completed_text = str(completed_messages[0].payload_json["text"])
            assert "Диагностика с сайта завершена" in completed_text
            assert "Сайт · AI-консультант" in completed_text
            assert "Радар спроса" in completed_text
            assert "Тип бизнеса: Услуги" in completed_text
            assert "Основная задача: Не забывать вернуться к клиенту" in completed_text
            assert report_command.summary in completed_text

            admin = await AdminLeadReadService(session).list_recent()
            website_view = next(item for item in admin.items if item.user_id == website_user_id)
            assert website_view.source == "website_consultant"
            assert website_view.source_label == "Сайт · AI-консультант"
            assert website_view.entry_code == "site_consultant_radar"
            assert website_view.intent == "radar"
            assert website_view.diagnostic_status == "diagnostic_completed"
            assert website_view.diagnostic_summary == report_command.summary

            consultation = ConsultationRequest(
                user_id=website_user_id,
                diagnostic_session_id=prepared.diagnostic_session_id,
            )
            session.add(consultation)
            await session.flush()
            await OpsNotificationService(session).enqueue_created_consultation(consultation)
            await OpsNotificationService(session).enqueue_created_consultation(consultation)

        async with session_scope(factory) as session:
            consultation_messages = (
                await session.scalars(
                    select(OutboundMessage).where(
                        OutboundMessage.dedupe_key.like("ops:consultation-created:%")
                    )
                )
            ).all()
            assert len(consultation_messages) == 1
            assert "Новая консультация AI My Time" in str(
                consultation_messages[0].payload_json["text"]
            )

        await _assert_unknown_payload_keeps_conference_behavior(factory)
    finally:
        await _clear(factory)
        await factory.kw["bind"].dispose()


async def _assert_unknown_payload_keeps_conference_behavior(factory) -> None:
    async with session_scope(factory) as session:
        legacy = await ConferenceIntakeService(session).start(
            ConferenceStartCommand(
                telegram_user_id="910002",
                qr_code="unknown_campaign_payload",
                entry_code="unknown_campaign_payload",
            )
        )
        touchpoint = await session.scalar(
            select(Touchpoint).where(Touchpoint.user_id == legacy.user_id)
        )
        assert touchpoint is not None
        assert touchpoint.source_code == "conference_2026"
        assert touchpoint.entry_code == "unknown_campaign_payload"
        await ProfileService(session).save(
            SaveProfileAnswersCommand(
                user_id=legacy.user_id,
                complete=True,
                answers=[
                    {"question_code": "business_type", "value": "Услуги"},
                    {"question_code": "team_size", "value": "1–3"},
                    {"question_code": "client_flow", "value": "Звонки"},
                    {"question_code": "current_tools", "value": "В чатах"},
                    {"question_code": "primary_pain", "value": "Время"},
                    {"question_code": "automation_goal", "value": "Быстрее отвечать клиентам"},
                ],
            )
        )
        prepared = await DiagnosticPreparationService(session).prepare(
            PrepareDiagnosticCommand(user_id=legacy.user_id)
        )

    async with session_scope(factory) as session:
        later_website_start = await WebsiteIntakeService(session).start(
            WebsiteStartCommand(
                telegram_user_id="910002",
                entry_code="site_consultant_radar",
                interaction_id="telegram-update:conference-diagnostic-later-website",
            )
        )
        assert later_website_start.created_touchpoint is True

    command = RecordDiagnosticReportCommand(
        diagnostic_session_id=prepared.diagnostic_session_id,
        summary="Conference regression summary.",
        priorities=[
            {
                "title": "Статус",
                "reason": "Проверка legacy-пути",
                "confidence": "medium",
            }
        ],
        next_steps=[{"title": "Шаг", "action": "Сохранить прежнее поведение"}],
    )
    async with session_scope(factory) as session:
        report = await DiagnosticReportService(session).record(command)
        assert report.created is True
    async with session_scope(factory) as session:
        assert await session.scalar(
            select(func.count())
            .select_from(OutboundMessage)
            .where(
                OutboundMessage.dedupe_key
                == f"ops:website-diagnostic-completed:{report.report_id}"
            )
        ) == 0


async def _clear(factory) -> None:
    async with session_scope(factory) as session:
        await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
