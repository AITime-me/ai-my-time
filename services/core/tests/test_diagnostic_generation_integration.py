"""Prove the future AI boundary with a deterministic local provider double."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import func, select, text

from app.db.session import create_session_factory, session_scope
from app.models import DiagnosticSession, OutboundMessage
from app.schemas.conference import ConferenceStartCommand
from app.schemas.diagnostic import PrepareDiagnosticCommand
from app.schemas.diagnostic_report import DiagnosticNextStepInput, DiagnosticPriorityInput
from app.schemas.profile import SaveProfileAnswersCommand
from app.services.conference_intake import ConferenceIntakeService
from app.services.diagnostic import DiagnosticPreparationService
from app.services.diagnostic_generation import (
    DiagnosticGenerationService,
    DiagnosticInput,
    GeneratedDiagnostic,
)
from app.services.profile import ProfileService


def _test_database_url() -> str:
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AI_MY_TIME_TEST_DATABASE_URL is not set")
    if not url.startswith("postgresql+asyncpg://") or "ai_my_time_test" not in url:
        raise RuntimeError("integration tests require the dedicated ai_my_time_test database")
    return url


class DeterministicProvider:
    def __init__(self) -> None:
        self.inputs: list[DiagnosticInput] = []

    async def generate(self, diagnostic_input: DiagnosticInput) -> GeneratedDiagnostic:
        self.inputs.append(diagnostic_input)
        return GeneratedDiagnostic(
            summary="Следующий шаг по заявке нужно сделать видимым для команды.",
            priorities=[
                DiagnosticPriorityInput(
                    title="Статус заявки", reason="Ручная передача не фиксируется", confidence="high"
                )
            ],
            next_steps=[
                DiagnosticNextStepInput(
                    title="Единый вход", action="Зафиксировать один канал новых заявок"
                )
            ],
            limitations=["Результат основан на ответах анкеты."],
        )


def test_diagnostic_provider_contract_is_snapshot_bound_and_idempotent() -> None:
    asyncio.run(_run_generation(_test_database_url()))


async def _run_generation(database_url: str) -> None:
    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
            entry = await ConferenceIntakeService(session).start(
                ConferenceStartCommand(telegram_user_id="900004", qr_code="qr_conf_main")
            )
            await ProfileService(session).save(
                SaveProfileAnswersCommand(
                    user_id=entry.user_id,
                    answers=[
                        {"question_code": "business_type", "value": "Услуги"},
                        {"question_code": "team_size", "value": "4–10"},
                        {"question_code": "client_flow", "value": "Мессенджеры"},
                        {"question_code": "current_tools", "value": "В чатах"},
                        {"question_code": "primary_pain", "value": "Заявки"},
                        {"question_code": "automation_goal", "value": "Не забывать вернуться к клиенту"},
                    ],
                    complete=True,
                )
            )
            prepared = await DiagnosticPreparationService(session).prepare(
                PrepareDiagnosticCommand(user_id=entry.user_id)
            )
        provider = DeterministicProvider()
        async with session_scope(factory) as session:
            service = DiagnosticGenerationService(session, provider)
            first = await service.complete(diagnostic_session_id=prepared.diagnostic_session_id)
            second = await service.complete(diagnostic_session_id=prepared.diagnostic_session_id)
            assert first.created is True
            assert second.created is False
        assert len(provider.inputs) == 1
        assert provider.inputs[0].diagnostic_session_id == prepared.diagnostic_session_id
        assert "900004" not in str(provider.inputs[0].profile_snapshot)
        async with session_scope(factory) as session:
            assert await session.scalar(select(func.count()).select_from(DiagnosticSession)) == 1
            assert await session.scalar(select(func.count()).select_from(OutboundMessage)) == 1
            payload = await session.scalar(select(OutboundMessage.payload_json))
            assert payload is not None
            assert payload["kind"] == "diagnostic_result"
    finally:
        try:
            async with session_scope(factory) as session:
                await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        finally:
            await factory.kw["bind"].dispose()
