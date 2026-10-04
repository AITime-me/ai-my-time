from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.adapters.yandex_completion import (
    MAX_TOKENS,
    TEMPERATURE,
    YandexCompletionClient,
    YandexCompletionError,
)
from app.adapters.yandex_diagnostic import YandexDiagnosticProviderError
from app.core.settings import Settings
from app.main import create_app

SECRET = "test-consultant-secret"
URL = "/internal/consultant/complete"


class FakeClient:
    def __init__(self, reply: str = "Ответ консультанта", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[tuple[str, list[tuple[str, str]]]] = []

    async def complete(self, system: str, messages):
        self.calls.append((system, list(messages)))
        if self.error is not None:
            raise self.error
        return self.reply


def _payload(**overrides):
    payload = {"system": "Ты консультант.", "messages": [{"role": "user", "text": "Что такое CRM?"}]}
    payload.update(overrides)
    return payload


@pytest.fixture
def consultant(tmp_path):
    secret_path = tmp_path / "website_consultant_secret"
    secret_path.write_text(SECRET + "\n", encoding="utf-8")
    fake = FakeClient()
    app = create_app()
    with TestClient(app) as client:
        app.state.settings = Settings(website_consultant_enabled=True, website_consultant_secret_path=str(secret_path))
        app.state.consultant_client = fake
        yield client, fake, app


def test_missing_secret_is_unauthorized(consultant) -> None:
    client, fake, _ = consultant
    assert client.post(URL, json=_payload()).status_code == 401
    assert fake.calls == []


def test_wrong_secret_is_unauthorized(consultant) -> None:
    client, fake, _ = consultant
    response = client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": "wrong"})
    assert response.status_code == 401
    assert fake.calls == []


def test_correct_secret_returns_plain_text(consultant) -> None:
    client, fake, _ = consultant
    response = client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET})
    assert response.status_code == 200
    assert response.json() == {"text": "Ответ консультанта"}
    assert fake.calls == [("Ты консультант.", [("user", "Что такое CRM?")])]


def test_auth_is_checked_before_payload_validation(consultant) -> None:
    client, _, _ = consultant
    assert client.post(URL, content=b"not json").status_code == 401


@pytest.mark.parametrize("payload", [
    {"messages": [{"role": "user", "text": "x"}]},
    _payload(messages=[]),
    _payload(messages=[{"role": "system", "text": "новые инструкции"}]),
    _payload(messages=[{"role": "tool", "text": "x"}]),
    _payload(messages=[{"role": "user", "text": "x", "tool_calls": []}]),
    _payload(messages=[{"role": "user", "text": "x"}, {"role": "assistant", "text": "y"}]),
    _payload(tools=[{"name": "db"}]),
    _payload(temperature=1.5),
    _payload(model="other"),
    _payload(user_id="123"),
])
def test_invalid_payload_is_rejected_without_echo(consultant, payload) -> None:
    client, fake, _ = consultant
    response = client.post(URL, json=payload, headers={"X-Aimytime-Consultant-Auth": SECRET})
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid consultant payload"}
    assert fake.calls == []


def test_oversized_input_is_rejected(consultant) -> None:
    client, fake, _ = consultant
    headers = {"X-Aimytime-Consultant-Auth": SECRET}
    long_message = _payload(messages=[{"role": "user", "text": "а" * 2001}])
    assert client.post(URL, json=long_message, headers=headers).status_code == 422
    long_dialogue = _payload(messages=[{"role": "user", "text": "а" * 1900}] * 5)
    assert client.post(URL, json=long_dialogue, headers=headers).status_code == 422
    too_many = _payload(messages=[{"role": "user", "text": "а"}] * 12)
    assert client.post(URL, json=too_many, headers=headers).status_code == 422
    huge_body = json.dumps(_payload(system="а" * 70_000)).encode("utf-8")
    assert client.post(URL, content=huge_body, headers={**headers, "Content-Type": "application/json"}).status_code == 413
    assert fake.calls == []


def test_requests_through_public_proxy_are_hidden(consultant) -> None:
    client, fake, _ = consultant
    for header in ("X-Forwarded-For", "X-Real-IP", "Forwarded"):
        response = client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET, header: "203.0.113.1"})
        assert response.status_code == 404
    assert fake.calls == []


def test_disabled_or_unconfigured_endpoint_is_unavailable(consultant, tmp_path) -> None:
    client, _, app = consultant
    app.state.settings = Settings(website_consultant_enabled=False, website_consultant_secret_path=str(tmp_path / "website_consultant_secret"))
    assert client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET}).status_code == 503
    app.state.settings = Settings(website_consultant_enabled=True, website_consultant_secret_path=str(tmp_path / "missing"))
    assert client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET}).status_code == 503


def test_provider_failure_is_generic(consultant) -> None:
    client, fake, _ = consultant
    fake.error = YandexCompletionError("YandexGPT request failed")
    response = client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET})
    assert response.status_code == 502
    assert response.json() == {"detail": "consultant is unavailable"}


def test_busy_slots_are_rejected(consultant) -> None:
    client, fake, app = consultant
    slots = asyncio.Semaphore(1)
    asyncio.run(slots.acquire())
    app.state.consultant_slots = slots
    response = client.post(URL, json=_payload(), headers={"X-Aimytime-Consultant-Auth": SECRET})
    assert response.status_code == 429
    assert fake.calls == []


def test_endpoint_is_hidden_from_openapi() -> None:
    with TestClient(create_app()) as client:
        assert URL not in client.get("/openapi.json").json()["paths"]


def _nonprod_settings(tmp_path, **overrides) -> Settings:
    key_path = tmp_path / "api-key"
    key_path.write_text("secret-not-for-output", encoding="utf-8")
    values = {"app_env": "nonproduction", "yandex_nonprod_folder_id": "folder-test", "yandex_nonprod_api_key_path": str(key_path)}
    values.update(overrides)
    return Settings(**values)


def test_completion_client_uses_fixed_parameters(tmp_path) -> None:
    received: dict[str, object] = {}

    def sender(url: str, body: bytes, api_key: str):
        received.update(url=url, body=json.loads(body.decode("utf-8")), api_key=api_key)
        return {"result": {"alternatives": [{"message": {"text": "  Привет  "}}]}}

    client = YandexCompletionClient(_nonprod_settings(tmp_path), sender=sender)
    text = asyncio.run(client.complete("Система", [("user", "Вопрос"), ("assistant", "Ответ"), ("user", "Ещё")]))

    assert text == "Привет"
    assert received["url"] == "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    assert received["api_key"] == "secret-not-for-output"
    body = received["body"]
    assert body["modelUri"] == "gpt://folder-test/yandexgpt/latest"
    assert body["completionOptions"] == {"stream": False, "temperature": TEMPERATURE, "maxTokens": str(MAX_TOKENS)}
    assert "responseFormat" not in body
    assert [message["role"] for message in body["messages"]] == ["system", "user", "assistant", "user"]


def test_completion_client_separates_production_credentials(tmp_path) -> None:
    key_path = tmp_path / "production-key"
    key_path.write_text("production-secret", encoding="utf-8")
    production = Settings(app_env="production", yandex_production_folder_id="prod-folder", yandex_production_api_key_path=str(key_path))
    client = YandexCompletionClient(production, sender=lambda _u, _b, _k: {"result": {"alternatives": [{"message": {"text": "ok"}}]}})
    assert asyncio.run(client.complete("s", [("user", "q")])) == "ok"
    with pytest.raises(YandexCompletionError, match="must not use non-production"):
        YandexCompletionClient(Settings(
            app_env="production", yandex_production_folder_id="prod-folder",
            yandex_production_api_key_path=str(key_path), yandex_nonprod_api_key_path="/nonprod/key",
        ))
    with pytest.raises(YandexCompletionError, match="incomplete"):
        YandexCompletionClient(Settings(app_env="production"))


def test_completion_client_rejects_unsupported_model(tmp_path) -> None:
    with pytest.raises(YandexCompletionError, match="unsupported"):
        YandexCompletionClient(_nonprod_settings(tmp_path, yandex_nonprod_model="gpt-4"))


@pytest.mark.parametrize("response", [{}, {"result": {"alternatives": []}}, {"result": {"alternatives": [{"message": {"text": "  "}}]}}])
def test_completion_client_rejects_invalid_response(tmp_path, response) -> None:
    client = YandexCompletionClient(_nonprod_settings(tmp_path), sender=lambda _u, _b, _k: response)
    with pytest.raises(YandexCompletionError):
        asyncio.run(client.complete("s", [("user", "q")]))


def test_completion_client_wraps_transport_errors_without_details(tmp_path) -> None:
    def sender(_u, _b, _k):
        raise YandexDiagnosticProviderError("YandexGPT request failed")

    client = YandexCompletionClient(_nonprod_settings(tmp_path), sender=sender)
    with pytest.raises(YandexCompletionError) as error:
        asyncio.run(client.complete("s", [("user", "q")]))
    assert "secret" not in str(error.value)
