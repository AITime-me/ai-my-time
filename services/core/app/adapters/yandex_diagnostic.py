"""Non-production YandexGPT adapter for the bounded diagnostic conversation."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.settings import Settings
from app.diagnostic_assets import load_diagnostic_prompt_bundle
from app.diagnostic_assets import normalize_diagnostic_result_v2, validate_diagnostic_result_v2
from app.services.diagnostic_generation import (
    DiagnosticConversationInput,
    DiagnosticConversationResponse,
)

_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
_LOG = logging.getLogger(__name__)


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
    """Uses a deliberately separated non-production or production credential."""

    def __init__(self, settings: Settings, sender: HttpSender = _post_json) -> None:
        if settings.diagnostic_provider == "yandex_nonprod":
            if settings.app_env == "production":
                raise YandexDiagnosticProviderError("YandexGPT non-production provider is disabled")
            folder_id = settings.yandex_nonprod_folder_id
            key_path = settings.yandex_nonprod_api_key_path
            model = settings.yandex_nonprod_model
        elif settings.diagnostic_provider == "yandex_production":
            if settings.app_env != "production":
                raise YandexDiagnosticProviderError("YandexGPT production provider is disabled")
            if settings.yandex_nonprod_folder_id or settings.yandex_nonprod_api_key_path:
                raise YandexDiagnosticProviderError("YandexGPT production must not use non-production configuration")
            folder_id = settings.yandex_production_folder_id
            key_path = settings.yandex_production_api_key_path
            model = settings.yandex_production_model
        else:
            raise YandexDiagnosticProviderError("YandexGPT provider is disabled")
        if not folder_id or not key_path:
            raise YandexDiagnosticProviderError("YandexGPT configuration is incomplete")
        if model != "yandexgpt/latest":
            raise YandexDiagnosticProviderError("unsupported YandexGPT model")
        self._folder_id = folder_id
        self._model = model
        self._key_path = Path(key_path)
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
                {"role": "system", "text": "\n\n".join((self._bundle.guardrails, self._bundle.prompt, self._bundle.knowledge_base, self._bundle.solution_catalog.model_dump_json()))},
                {"role": "user", "text": json.dumps({
                    "profile_snapshot": diagnostic_input.profile_snapshot,
                    "dialogue": [{"actor": actor, "content": content} for actor, content in diagnostic_input.turns],
                    "required_response": {
                        "question": "one short Russian question, or null",
                        "report": "null, or the complete DiagnosticResult v2 object",
                    },
                    "rule": "Ask a contextual question until enough evidence is present; do not exceed four user replies. Return JSON only.",
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
        # Application state remains authoritative: a report needs at least one
        # reply to the opening question and no conversation may exceed four.
        if isinstance(question, str) and question.strip() and (not isinstance(report, dict) or user_turn_count == 0):
            return DiagnosticConversationResponse(question=question.strip()[:1000])
        if isinstance(report, dict) and user_turn_count >= 1:
            try:
                normalized, normalized_fields = normalize_diagnostic_result_v2(report)
                if normalized_fields:
                    _LOG.info(
                        "normalized YandexGPT diagnostic result list overflow",
                        extra={"normalized_fields": normalized_fields},
                    )
                return DiagnosticConversationResponse(diagnostic=validate_diagnostic_result_v2(normalized))
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
    """Build only an explicitly configured provider with environment-separated credentials."""
    return YandexDiagnosticProvider(settings)
