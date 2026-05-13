from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import httpx

from meeting_mvp_backend.config import Settings

QWEN_INTERIM_TEMPERATURE = 0.2
QWEN_INTERIM_REQUEST_TIMEOUT_SECONDS = 8.0
QWEN_INTERIM_SYSTEM_PROMPT = (
    "你是英语会议的实时中文辅助翻译。把英文临时转写翻成简洁、自然、"
    "适合中国职场用户快速理解的中文；不扩写，不添加原文没有的信息；"
    "只输出中文译文。"
)


class InterimTranslationError(RuntimeError):
    """Raised when interim translation fails in a recoverable way."""


class InterimTranslationProvider(Protocol):
    async def translate_interim(self, text: str) -> str: ...

    async def close(self) -> None: ...


class QwenInterimTranslationProvider:
    def __init__(
        self,
        *,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        request_timeout_seconds: float = QWEN_INTERIM_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._settings = settings
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=request_timeout_seconds,
        )

    async def translate_interim(self, text: str) -> str:
        normalized_text = " ".join(text.split())
        if normalized_text == "":
            return ""

        try:
            response = await self._http_client.post(
                _qwen_chat_completions_url(self._settings),
                headers=_qwen_text_headers(self._settings),
                json=_qwen_interim_payload(self._settings, normalized_text),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise InterimTranslationError(
                f"Qwen interim translation HTTP error: {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise InterimTranslationError(
                f"Qwen interim translation transport error: {exc.__class__.__name__}",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise InterimTranslationError(
                "Qwen interim translation returned invalid JSON",
            ) from exc

        return _translation_text_from_response(payload)

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()


def create_qwen_interim_translation_provider_from_settings(
    settings: Settings,
) -> QwenInterimTranslationProvider:
    return QwenInterimTranslationProvider(settings=settings)


def _qwen_chat_completions_url(settings: Settings) -> str:
    base_url = _required_setting(settings.qwen_base_url, "QWEN_BASE_URL")
    return f"{base_url.rstrip('/')}/chat/completions"


def _qwen_text_headers(settings: Settings) -> dict[str, str]:
    api_key = _required_setting(settings.qwen_api_key, "QWEN_API_KEY")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _qwen_interim_payload(
    settings: Settings,
    text: str,
) -> dict[str, object]:
    model = _required_setting(settings.qwen_interim_model, "QWEN_INTERIM_MODEL")
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": QWEN_INTERIM_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        "temperature": QWEN_INTERIM_TEMPERATURE,
        "stream": False,
    }


def _translation_text_from_response(payload: object) -> str:
    if not isinstance(payload, Mapping):
        raise InterimTranslationError(
            "Qwen interim translation returned an invalid response shape",
        )

    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise InterimTranslationError(
            "Qwen interim translation returned no choices",
        )

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise InterimTranslationError(
            "Qwen interim translation returned an invalid choice",
        )

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise InterimTranslationError(
            "Qwen interim translation returned no message",
        )

    content = message.get("content")
    text = _content_to_text(content).strip()
    if text == "":
        raise InterimTranslationError(
            "Qwen interim translation returned empty text",
        )
    return text


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_content_part_to_text(part) for part in content)
    return ""


def _content_part_to_text(part: object) -> str:
    if isinstance(part, str):
        return part
    if not isinstance(part, Mapping):
        return ""
    value = part.get("text")
    return value if isinstance(value, str) else ""


def _required_setting(value: str | None, env_name: str) -> str:
    if value is None or value.strip() == "":
        raise InterimTranslationError(
            f"{env_name} is required for Qwen interim translation",
        )
    return value.strip()
