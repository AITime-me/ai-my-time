from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from app.adapters.yandex_diagnostic import YandexDiagnosticProvider, YandexDiagnosticProviderError
from app.core.settings import Settings
from app.services.diagnostic_generation import DiagnosticConversationInput


def _input() -> DiagnosticConversationInput:
    return DiagnosticConversationInput(
        diagnostic_session_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        profile_snapshot={"profile_answers": {"business_type": {"value": "Услуги"}}},
        turns=[],
    )


def test_provider_uses_bundle_and_parses_question(tmp_path) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret-not-for-output", encoding="utf-8")
    received: dict[str, object] = {}

    def sender(url: str, body: bytes, api_key: str):
        received.update(url=url, body=body.decode("utf-8"), api_key=api_key)
        return {"result": {"alternatives": [{"message": {"text": '{"question":"Кто принимает обращение первым?","report":null}'}}]}}

    provider = YandexDiagnosticProvider(Settings(
        app_env="nonproduction", diagnostic_provider="yandex_nonprod",
        yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
    ), sender=sender)
    response = asyncio.run(provider.advance(_input()))

    assert response.question == "Кто принимает обращение первым?"
    assert response.diagnostic is None
    assert received["url"] == "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    assert received["api_key"] == "secret-not-for-output"
    payload = json.loads(str(received["body"]))
    assert payload["modelUri"] == "gpt://folder-test/yandexgpt/latest"
    assert payload["responseFormat"] == {"jsonObject": {}}
    assert "System guardrails" in payload["messages"][0]["text"]
    assert "Diagnostic methodology knowledge base" in payload["messages"][0]["text"]
    assert "never choose `crm_automation` when the facts say CRM is absent" in payload["messages"][0]["text"]
    assert "choose `integrations_data_exchange`" in payload["messages"][0]["text"]
    assert "choose `lead_intake_contour`" in payload["messages"][0]["text"]
    assert "1–6 direct facts" in payload["messages"][0]["text"]
    assert '"id":"crm_implementation"' in payload["messages"][0]["text"]


def test_provider_is_fail_closed_in_production(tmp_path) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret", encoding="utf-8")
    with pytest.raises(YandexDiagnosticProviderError):
        YandexDiagnosticProvider(Settings(
            app_env="production", diagnostic_provider="yandex_nonprod",
            yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
        ))


def test_production_provider_requires_separate_production_configuration(tmp_path) -> None:
    key_path = tmp_path / "production-api-key"
    key_path.write_text("production-secret", encoding="utf-8")
    provider = YandexDiagnosticProvider(Settings(
        app_env="production", diagnostic_provider="yandex_production",
        yandex_production_folder_id="production-folder", yandex_production_api_key_path=str(key_path),
    ), sender=lambda _url, _body, _key: {"result": {"alternatives": [{"message": {"text": '{"question":"Кто отвечает?","report":null}'}}]}})
    assert asyncio.run(provider.advance(_input())).question == "Кто отвечает?"
    with pytest.raises(YandexDiagnosticProviderError, match="must not use non-production"):
        YandexDiagnosticProvider(Settings(
            app_env="production", diagnostic_provider="yandex_production",
            yandex_production_folder_id="production-folder", yandex_production_api_key_path=str(key_path),
            yandex_nonprod_api_key_path="/nonprod/key",
        ))


def test_provider_accepts_json_fence(tmp_path) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret", encoding="utf-8")
    provider = YandexDiagnosticProvider(Settings(
        app_env="nonproduction", diagnostic_provider="yandex_nonprod",
        yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
    ), sender=lambda _url, _body, _key: {"result": {"alternatives": [{"message": {"text": "```json\n{\"question\":\"Кто отвечает?\",\"report\":null}\n```"}}]}})
    assert asyncio.run(provider.advance(_input())).question == "Кто отвечает?"


def test_provider_prefers_question_before_two_replies(tmp_path) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret", encoding="utf-8")
    provider = YandexDiagnosticProvider(Settings(
        app_env="nonproduction", diagnostic_provider="yandex_nonprod",
        yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
    ), sender=lambda _url, _body, _key: {"result": {"alternatives": [{"message": {"text": '{"question":"Кто отвечает?","report":{"summary":"x","priorities":[],"next_steps":[]}}'}}]}})
    assert asyncio.run(provider.advance(_input())).question == "Кто отвечает?"


def test_provider_normalizes_overflowed_responsibilities_before_v2_validation(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret", encoding="utf-8")
    report = {
        "contract_version": "v2",
        "evidence": {"facts": ["Заявки теряются между сменами"]},
        "mechanism": "Передача не закрепляет ответственного.",
        "problem_types": ["execution_gap", "observability_gap"],
        "problem_scale": "process",
        "solution_class_id": "lead_intake_contour",
        "client_view": {
            "what_is_happening": "Заявки передаются вручную.",
            "where_result_is_lost": "Не видно следующего шага.",
            "future_process": "Передача фиксируется с ответственным.",
            "system_responsibilities": ["Фиксировать передачу", "Назначать ответственного", "Напоминать", "Собирать статистику", "Показывать очередь"],
            "ai_responsibilities": ["Классифицировать", "Подсказать", "Суммировать", "Лишний пункт"],
            "human_responsibilities": ["Решать исключения", "Проверять качество", "Выбирать правило", "Лишний пункт"],
        },
    }
    provider = YandexDiagnosticProvider(Settings(
        app_env="nonproduction", diagnostic_provider="yandex_nonprod",
        yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
    ), sender=lambda _url, _body, _key: {"result": {"alternatives": [{"message": {"text": json.dumps({"question": None, "report": report})}}]}})
    with caplog.at_level("INFO"):
        response = provider._parse(
            {"result": {"alternatives": [{"message": {"text": json.dumps({"question": None, "report": report})}}]}},
            user_turn_count=1,
        )

    assert response.question is None
    assert response.diagnostic is not None
    assert response.diagnostic.problem_types == ["execution_gap", "observability_gap"]
    assert response.diagnostic.client_view.system_responsibilities == report["client_view"]["system_responsibilities"][:3]
    assert response.diagnostic.client_view.ai_responsibilities == report["client_view"]["ai_responsibilities"][:3]
    assert response.diagnostic.client_view.human_responsibilities == report["client_view"]["human_responsibilities"][:3]
    assert "normalized YandexGPT diagnostic result list overflow" in caplog.text
