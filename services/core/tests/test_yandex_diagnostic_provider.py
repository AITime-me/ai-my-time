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


def test_provider_is_fail_closed_in_production(tmp_path) -> None:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret", encoding="utf-8")
    with pytest.raises(YandexDiagnosticProviderError):
        YandexDiagnosticProvider(Settings(
            app_env="production", diagnostic_provider="yandex_nonprod",
            yandex_nonprod_folder_id="folder-test", yandex_nonprod_api_key_path=str(key_path),
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
