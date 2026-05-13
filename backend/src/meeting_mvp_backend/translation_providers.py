from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx

from meeting_mvp_backend.config import Settings

QWEN_FINAL_TEMPERATURE = 0.1
QWEN_FINAL_REQUEST_TIMEOUT_SECONDS = 60.0
QWEN_FINAL_CONTEXT_SEGMENT_LIMIT = 5
QWEN_FINAL_SYSTEM_PROMPT = (
    "你是英语会议的正式会议中文翻译。把英文 final 片段翻译成准确、自然、"
    "适合中国职场用户阅读和归档的中文；保留人名、产品名、公司名、数字、"
    "日期、金额和业务术语；不要扩写，不要总结，不添加原文没有的信息；"
    "只输出当前片段的中文译文。"
)
QWEN_INTERIM_TEMPERATURE = 0.2
QWEN_INTERIM_REQUEST_TIMEOUT_SECONDS = 8.0
QWEN_INTERIM_SYSTEM_PROMPT = (
    "你是英语会议的实时中文辅助翻译。把英文临时转写翻成简洁、自然、"
    "适合中国职场用户快速理解的中文；不扩写，不添加原文没有的信息；"
    "只输出中文译文。"
)


class TranslationProviderError(RuntimeError):
    """Base class for recoverable translation provider failures."""


class InterimTranslationError(TranslationProviderError):
    """Raised when interim translation fails in a recoverable way."""


class FinalTranslationError(TranslationProviderError):
    """Raised when final translation fails in a recoverable way."""


@dataclass(frozen=True, slots=True)
class FinalTranslationContextSegment:
    sequence: int
    english_text_final: str
    chinese_text_final: str


@dataclass(frozen=True, slots=True)
class FinalTranslationRequest:
    sequence: int
    text: str
    context: tuple[FinalTranslationContextSegment, ...] = ()


class InterimTranslationProvider(Protocol):
    async def translate_interim(self, text: str) -> str: ...

    async def close(self) -> None: ...


class FinalTranslationProvider(Protocol):
    async def translate_final(self, request: FinalTranslationRequest) -> str: ...

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
                _qwen_chat_completions_url(
                    self._settings,
                    InterimTranslationError,
                    "Qwen interim translation",
                ),
                headers=_qwen_text_headers(
                    self._settings,
                    InterimTranslationError,
                    "Qwen interim translation",
                ),
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

        return _translation_text_from_response(payload, InterimTranslationError)

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()


class QwenFinalTranslationProvider:
    def __init__(
        self,
        *,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        request_timeout_seconds: float = QWEN_FINAL_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._settings = settings
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=request_timeout_seconds,
        )

    async def translate_final(self, request: FinalTranslationRequest) -> str:
        normalized_text = " ".join(request.text.split())
        if normalized_text == "":
            return ""

        try:
            response = await self._http_client.post(
                _qwen_chat_completions_url(
                    self._settings,
                    FinalTranslationError,
                    "Qwen final translation",
                ),
                headers=_qwen_text_headers(
                    self._settings,
                    FinalTranslationError,
                    "Qwen final translation",
                ),
                json=_qwen_final_payload(self._settings, request, normalized_text),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FinalTranslationError(
                f"Qwen final translation HTTP error: {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise FinalTranslationError(
                f"Qwen final translation transport error: {exc.__class__.__name__}",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise FinalTranslationError(
                "Qwen final translation returned invalid JSON",
            ) from exc

        return _translation_text_from_response(payload, FinalTranslationError)

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()


def create_qwen_interim_translation_provider_from_settings(
    settings: Settings,
) -> QwenInterimTranslationProvider:
    return QwenInterimTranslationProvider(settings=settings)


def create_qwen_final_translation_provider_from_settings(
    settings: Settings,
) -> QwenFinalTranslationProvider:
    return QwenFinalTranslationProvider(settings=settings)


def _qwen_chat_completions_url(
    settings: Settings,
    error_cls: type[TranslationProviderError],
    purpose: str,
) -> str:
    base_url = _required_setting(
        settings.qwen_base_url,
        "QWEN_BASE_URL",
        error_cls,
        purpose,
    )
    return f"{base_url.rstrip('/')}/chat/completions"


def _qwen_text_headers(
    settings: Settings,
    error_cls: type[TranslationProviderError],
    purpose: str,
) -> dict[str, str]:
    api_key = _required_setting(
        settings.qwen_api_key,
        "QWEN_API_KEY",
        error_cls,
        purpose,
    )
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _qwen_interim_payload(
    settings: Settings,
    text: str,
) -> dict[str, object]:
    model = _required_setting(
        settings.qwen_interim_model,
        "QWEN_INTERIM_MODEL",
        InterimTranslationError,
        "Qwen interim translation",
    )
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


def _qwen_final_payload(
    settings: Settings,
    request: FinalTranslationRequest,
    normalized_text: str,
) -> dict[str, object]:
    model = _required_setting(
        settings.qwen_final_model,
        "QWEN_FINAL_MODEL",
        FinalTranslationError,
        "Qwen final translation",
    )
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": QWEN_FINAL_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": _qwen_final_user_content(request, normalized_text),
            },
        ],
        "enable_thinking": False,
        "max_tokens": 512,
        "temperature": QWEN_FINAL_TEMPERATURE,
        "stream": False,
    }


def _qwen_final_user_content(
    request: FinalTranslationRequest,
    normalized_text: str,
) -> str:
    context_segments = request.context[-QWEN_FINAL_CONTEXT_SEGMENT_LIMIT:]
    if context_segments:
        context_text = "\n".join(
            (
                f"{segment.sequence}. English: {segment.english_text_final}\n"
                f"   中文: {segment.chinese_text_final}"
            )
            for segment in context_segments
        )
    else:
        context_text = "无"

    return (
        "最近已确认的双语上下文（仅用于术语和指代一致性）：\n"
        f"{context_text}\n\n"
        f"当前英文 final 片段（sequence={request.sequence}）：\n"
        f"{normalized_text}\n\n"
        "请只输出当前片段的正式中文译文。"
    )


def _translation_text_from_response(
    payload: object,
    error_cls: type[TranslationProviderError],
) -> str:
    if not isinstance(payload, Mapping):
        raise error_cls(
            "Qwen translation returned an invalid response shape",
        )

    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise error_cls(
            "Qwen translation returned no choices",
        )

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise error_cls(
            "Qwen translation returned an invalid choice",
        )

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise error_cls(
            "Qwen translation returned no message",
        )

    content = message.get("content")
    text = _content_to_text(content).strip()
    if text == "":
        raise error_cls(
            "Qwen translation returned empty text",
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


def _required_setting(
    value: str | None,
    env_name: str,
    error_cls: type[TranslationProviderError],
    purpose: str,
) -> str:
    if value is None or value.strip() == "":
        raise error_cls(
            f"{env_name} is required for {purpose}",
        )
    return value.strip()
