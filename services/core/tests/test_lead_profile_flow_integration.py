"""Real PostgreSQL proof for durable profile states and outbox de-duplication."""

from __future__ import annotations

import asyncio
import copy
import os

import pytest
from sqlalchemy import func, select, text

from app.db.session import create_session_factory, session_scope
from app.models import DiagnosticSession, LeadBotSession, OutboundMessage
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.lead_profile_flow import LeadProfileFlow, PROFILE_STEPS
from app.services.profile import ProfileService
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
    assert all(
        len(f"profile:v2:999:{step.code}:{index}".encode("utf-8")) <= 64
        for step in PROFILE_STEPS
        for index, _option in enumerate(step.options)
    )


def test_legacy_prepared_explicit_restart_opens_one_v2_flow_and_preserves_snapshot() -> None:
    asyncio.run(_run_legacy_restart(_test_database_url()))


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
            active = await flow.start(user_id=entry.user_id)
            repeated = await flow.start(user_id=entry.user_id)
            assert repeated.id == active.id and repeated.version == active.version

        async with session_scope(factory) as session:
            flow = LeadProfileFlow(session, ScriptedDiagnosticProvider())
            flow_row = await session.scalar(select(LeadBotSession).where(LeadBotSession.user_id == entry.user_id))
            assert flow_row is not None
            for step in PROFILE_STEPS:
                result = await flow.answer(
                    user_id=entry.user_id,
                    question_code=step.code,
                    flow_version=flow_row.version,
                    option_index=0,
                )
                flow_row = result
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


async def _run_legacy_restart(database_url: str) -> None:
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
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(telegram_user_id="900003", qr_code="qr_conf_main")
            )
            await ProfileService(session).save(
                SaveProfileAnswersCommand(
                    user_id=entry.user_id,
                    complete=True,
                    answers=[{"question_code": step.code, "value": step.options[0]} for step in PROFILE_STEPS],
                )
            )
            legacy = await DiagnosticPreparationService(session).prepare(
                PrepareDiagnosticCommand(user_id=entry.user_id)
            )
            legacy_session = await session.get(DiagnosticSession, legacy.diagnostic_session_id)
            assert legacy_session is not None
            legacy_snapshot = copy.deepcopy(legacy_session.input_snapshot_json)
            session.add(
                LeadBotSession(
                    user_id=entry.user_id,
                    state="complete",
                    status="completed",
                    version=7,
                    flow_version="legacy",
                )
            )
            await session.flush()

            flow = LeadProfileFlow(session, ScriptedDiagnosticProvider())
            v2 = await flow.start(user_id=entry.user_id)
            assert (v2.flow_version, v2.status, v2.state, v2.version) == ("v2", "open", "business_type", 8)
            repeated = await flow.start(user_id=entry.user_id)
            assert repeated.id == v2.id and repeated.version == 8
            assert await session.scalar(select(func.count()).select_from(OutboundMessage)) == 1
            assert legacy_session.input_snapshot_json == legacy_snapshot

            # A callback issued by the old unversioned legacy keyboard cannot
            # advance the fresh v2 state.
            with pytest.raises(ValueError, match="unexpected"):
                await flow.answer(
                    user_id=entry.user_id,
                    question_code="business_type",
                    flow_version=None,
                )
            assert v2.state == "business_type" and v2.version == 8

            current = v2
            for step in PROFILE_STEPS:
                current = await flow.answer(
                    user_id=entry.user_id,
                    question_code=step.code,
                    flow_version=current.version,
                    option_index=0,
                )
            assert current.status == "completed"
            diagnostics = (
                await session.scalars(
                    select(DiagnosticSession)
                    .where(DiagnosticSession.user_id == entry.user_id)
                    .order_by(DiagnosticSession.created_at)
                )
            ).all()
            assert len(diagnostics) == 2
            assert diagnostics[0].id == legacy.diagnostic_session_id
            assert diagnostics[0].status == "prepared"
            assert diagnostics[0].input_snapshot_json == legacy_snapshot
            assert diagnostics[1].id != diagnostics[0].id
            messages = (await session.scalars(select(OutboundMessage))).all()
            assert len({message.dedupe_key for message in messages}) == len(messages)
            assert await session.scalar(select(func.count()).select_from(OutboundMessage)) == 7
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
