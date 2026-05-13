from __future__ import annotations

import json

import httpx
import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.translation_providers import (
    InterimTranslationError,
    QwenInterimTranslationProvider,
)


def qwen_text_settings() -> Settings:
    settings = Settings()
    settings.qwen_api_key = "test-qwen-key"
    settings.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    settings.qwen_interim_model = "qwen-turbo"
    return settings


@pytest.mark.asyncio
async def test_qwen_interim_provider_posts_openai_compatible_chat_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "我们需要在周五前对齐上线时间线。",
                        },
                    },
                ],
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        provider = QwenInterimTranslationProvider(
            settings=qwen_text_settings(),
            http_client=http_client,
        )

        result = await provider.translate_interim(
            "We need to align on the launch timeline before Friday.",
        )

    assert result == "我们需要在周五前对齐上线时间线。"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    assert request.headers["authorization"] == "Bearer test-qwen-key"
    payload = json.loads(request.content)
    assert payload["model"] == "qwen-turbo"
    assert payload["temperature"] == 0.2
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert "只输出中文译文" in payload["messages"][0]["content"]
    assert payload["messages"][1] == {
        "role": "user",
        "content": "We need to align on the launch timeline before Friday.",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "expected_env"),
    [
        ("qwen_api_key", "QWEN_API_KEY"),
        ("qwen_base_url", "QWEN_BASE_URL"),
        ("qwen_interim_model", "QWEN_INTERIM_MODEL"),
    ],
)
async def test_qwen_interim_provider_reports_missing_config_name_only(
    field_name: str,
    expected_env: str,
) -> None:
    settings = qwen_text_settings()
    setattr(settings, field_name, None)
    provider = QwenInterimTranslationProvider(settings=settings)

    with pytest.raises(InterimTranslationError, match=expected_env) as exc_info:
        await provider.translate_interim("We need to align.")

    assert "test-qwen-key" not in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, json={"error": {"code": "rate_limit"}}),
        httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]}),
        httpx.Response(200, content=b"{not-json"),
    ],
)
async def test_qwen_interim_provider_wraps_http_empty_and_json_failures(
    response: httpx.Response,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        provider = QwenInterimTranslationProvider(
            settings=qwen_text_settings(),
            http_client=http_client,
        )

        with pytest.raises(InterimTranslationError):
            await provider.translate_interim("We need to align.")
