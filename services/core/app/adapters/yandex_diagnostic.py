"""Non-production YandexGPT adapter for the bounded diagnostic conversation."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.diagnostic_assets import load_diagnostic_prompt_bundle
from app.schemas.diagnostic_report import DiagnosticNextStepInput, DiagnosticPriorityInput, DiagnosticRoleSplitInput
from app.services.diagnostic_generation import (
    DiagnosticConversationInput,
    DiagnosticConversationResponse,
    GeneratedDiagnostic,
)

_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexDiagnosticProviderError(RuntimeError):
    """A safe failure that never includes credentials or provider response text."""


HttpSender = Callable[[str, bytes, str], dict[str, Any]]


def _post_json(url: str, body: bytes, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Authorization", f"Api-Key {api_key}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310 -- fixed YC endpoint
            decoded = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise YandexDiagnosticProviderError("YandexGPT request failed") from error
    if not isinstance(decoded, dict):
        raise YandexDiagnosticProviderError("YandexGPT response is invalid")
    return decoded


class YandexDiagnosticProvider:
    """Uses only the configured non-production folder and versioned text bundle."""

    def __init__(self, settings: Settings, sender: HttpSender = _post_json) -> None:
        if settings.app_env == "production" or settings.diagnostic_provider != "yandex_nonprod":
            raise YandexDiagnosticProviderError("YandexGPT non-production provider is disabled")
        if not settings.yandex_nonprod_folder_id or not settings.yandex_nonprod_api_key_path:
            raise YandexDiagnosticProviderError("YandexGPT non-production configuration is incomplete")
        if settings.yandex_nonprod_model != "yandexgpt/latest":
            raise YandexDiagnosticProviderError("unsupported YandexGPT non-production model")
        self._folder_id = settings.yandex_nonprod_folder_id
        self._model = settings.yandex_nonprod_model
        self._key_path = Path(settings.yandex_nonprod_api_key_path)
        self._bundle = load_diagnostic_prompt_bundle(settings.diagnostic_prompt_version)
        self._sender = sender

    async def advance(self, diagnostic_input: DiagnosticConversationInput) -> DiagnosticConversationResponse:
        api_key = self._read_key()
        body = self._request_body(diagnostic_input)
        response = await asyncio.to_thread(self._sender, _URL, body, api_key)
        user_turn_count = sum(1 for actor, _content in diagnostic_input.turns if actor == "user")
        return self._parse(response, user_turn_count)

    def _read_key(self) -> str:
        try:
            key = self._key_path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise YandexDiagnosticProviderError("YandexGPT API key is unavailable") from error
        if not key:
            raise YandexDiagnosticProviderError("YandexGPT API key is unavailable")
        return key

    def _request_body(self, diagnostic_input: DiagnosticConversationInput) -> bytes:
        payload = {
            "modelUri": f"gpt://{self._folder_id}/{self._model}",
            # A compact Russian report can still exceed the provider's short
            # completion budget when it must close valid JSON.
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": "2500"},
            "messages": [
                {"role": "system", "text": "\n\n".join((self._bundle.guardrails, self._bundle.prompt, self._bundle.knowledge_base))},
                {"role": "user", "text": json.dumps({
                    "profile_snapshot": diagnostic_input.profile_snapshot,
                    "dialogue": [{"actor": actor, "content": content} for actor, content in diagnostic_input.turns],
                    "required_response": {
                        "question": "one short Russian question, or null",
                        "report": "null, or the complete DiagnosticResult v1 object",
                    },
                    "rule": "Ask a contextual question until enough evidence is present; after 2-4 user replies return report and question null. Return JSON only.",
                }, ensure_ascii=False)},
            ],
            # Native JSON mode prevents Markdown/prose around the contract.
            "responseFormat": {"jsonObject": {}},
        }
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _parse(self, response: dict[str, Any], user_turn_count: int = 0) -> DiagnosticConversationResponse:
        try:
            text = response["result"]["alternatives"][0]["message"]["text"]
            raw = json.loads(_json_text(text))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise YandexDiagnosticProviderError("YandexGPT returned an invalid diagnostic response") from error
        if not isinstance(raw, dict):
            raise YandexDiagnosticProviderError("YandexGPT returned an invalid diagnostic response")
        question = raw.get("question")
        report = raw.get("report")
        # The model occasionally returns both fields despite the prompt. The
        # bounded application state is authoritative: questions before two
        # replies, report afterwards. This keeps the provider from extending
        # the dialogue or leaking a premature report.
        if isinstance(question, str) and question.strip() and (user_turn_count < 2 or not isinstance(report, dict)):
            return DiagnosticConversationResponse(question=question.strip()[:1000])
        if isinstance(report, dict) and user_turn_count >= 2:
            try:
                return DiagnosticConversationResponse(diagnostic=GeneratedDiagnostic(
                    summary=report["summary"],
                    priorities=[DiagnosticPriorityInput.model_validate(item) for item in report["priorities"]],
                    next_steps=[DiagnosticNextStepInput.model_validate(item) for item in report["next_steps"]],
                    limitations=list(report.get("limitations", [])),
                    role_split=DiagnosticRoleSplitInput.model_validate(report.get("role_split", {})),
                ))
            except (KeyError, TypeError, ValueError) as error:
                raise YandexDiagnosticProviderError("YandexGPT returned an invalid diagnostic report") from error
        raise YandexDiagnosticProviderError("YandexGPT returned an invalid diagnostic response")


def _json_text(value: object) -> str:
    """Accept an accidental Markdown JSON fence, but no prose or partial JSON."""
    if not isinstance(value, str):
        raise TypeError("model text is not a string")
    text = value.strip()
    if text.startswith("```"):
        parts = text.splitlines()
        if len(parts) < 3 or not parts[-1].strip().startswith("```"):
            raise ValueError("unterminated JSON fence")
        text = "\n".join(parts[1:-1]).strip()
    return text


def build_diagnostic_provider(settings: Settings) -> YandexDiagnosticProvider:
    """The only runtime provider factory: disabled unless nonprod is explicit."""
    return YandexDiagnosticProvider(settings)
