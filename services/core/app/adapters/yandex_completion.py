"""Plain-text YandexGPT completion for the website consultant.

Model parameters are fixed here on purpose: callers supply only the dialogue.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from app.adapters.yandex_diagnostic import YandexDiagnosticProviderError, _URL, _post_json
from app.core.settings import Settings

MAX_TOKENS = 600
TEMPERATURE = 0.3
TIMEOUT_SECONDS = 15
MAX_REPLY_CHARS = 4_000
_SUPPORTED_MODELS = frozenset({"yandexgpt/latest", "yandexgpt-lite/latest"})

CompletionSender = Callable[[str, bytes, str], dict[str, Any]]


class YandexCompletionError(RuntimeError):
    """A safe failure that never includes credentials or provider response text."""


def _default_sender(url: str, body: bytes, api_key: str) -> dict[str, Any]:
    return _post_json(url, body, api_key, timeout=TIMEOUT_SECONDS)


class YandexCompletionClient:
    def __init__(self, settings: Settings, sender: CompletionSender = _default_sender) -> None:
        if settings.app_env == "production":
            if settings.yandex_nonprod_folder_id or settings.yandex_nonprod_api_key_path:
                raise YandexCompletionError("YandexGPT production must not use non-production configuration")
            folder_id = settings.yandex_production_folder_id
            key_path = settings.yandex_production_api_key_path
            model = settings.yandex_production_model
        else:
            folder_id = settings.yandex_nonprod_folder_id
            key_path = settings.yandex_nonprod_api_key_path
            model = settings.yandex_nonprod_model
        if not folder_id or not key_path:
            raise YandexCompletionError("YandexGPT configuration is incomplete")
        if model not in _SUPPORTED_MODELS:
            raise YandexCompletionError("unsupported YandexGPT model")
        self._model_uri = f"gpt://{folder_id}/{model}"
        self._key_path = Path(key_path)
        self._sender = sender

    async def complete(self, system: str, messages: Sequence[tuple[str, str]]) -> str:
        api_key = self._read_key()
        body = json.dumps({
            "modelUri": self._model_uri,
            "completionOptions": {"stream": False, "temperature": TEMPERATURE, "maxTokens": str(MAX_TOKENS)},
            "messages": [{"role": "system", "text": system}, *({"role": role, "text": text} for role, text in messages)],
        }, ensure_ascii=False).encode("utf-8")
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self._sender, _URL, body, api_key), timeout=TIMEOUT_SECONDS + 2,
            )
        except (YandexDiagnosticProviderError, TimeoutError) as error:
            raise YandexCompletionError("YandexGPT request failed") from error
        try:
            text = response["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise YandexCompletionError("YandexGPT response is invalid") from error
        if not isinstance(text, str) or not text.strip():
            raise YandexCompletionError("YandexGPT response is empty")
        return text.strip()[:MAX_REPLY_CHARS]

    def _read_key(self) -> str:
        try:
            key = self._key_path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise YandexCompletionError("YandexGPT API key is unavailable") from error
        if not key:
            raise YandexCompletionError("YandexGPT API key is unavailable")
        return key
