from __future__ import annotations

import json

import httpx
import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.translation_providers import (
    FinalTranslationContextSegment,
    FinalTranslationError,
    FinalTranslationRequest,
    InterimTranslationError,
    QwenFinalTranslationProvider,
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


@pytest.mark.asyncio
async def test_qwen_final_provider_posts_contextual_chat_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "请确认 Acme 上线是否仍安排在周五。",
                        },
                    },
                ],
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        provider = QwenFinalTranslationProvider(
            settings=qwen_text_settings(),
            http_client=http_client,
        )

        result = await provider.translate_final(
            FinalTranslationRequest(
                sequence=7,
                text="Can you confirm the Acme rollout still lands on Friday?",
                context=(
                    FinalTranslationContextSegment(
                        sequence=5,
                        english_text_final="Acme rollout is blocked by budget review.",
                        chinese_text_final="Acme 上线受预算审查阻塞。",
                    ),
                    FinalTranslationContextSegment(
                        sequence=6,
                        english_text_final="Finance will finish the review tomorrow.",
                        chinese_text_final="财务会在明天完成审查。",
                    ),
                ),
            ),
        )

    assert result == "请确认 Acme 上线是否仍安排在周五。"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    assert request.headers["authorization"] == "Bearer test-qwen-key"
    payload = json.loads(request.content)
    assert payload["model"] == "qwen3.6-max-preview"
    assert payload["enable_thinking"] is False
    assert payload["max_tokens"] == 512
    assert payload["temperature"] == 0.1
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert "正式会议中文翻译" in payload["messages"][0]["content"]
    user_content = payload["messages"][1]["content"]
    assert "最近已确认的双语上下文" in user_content
    assert "Acme rollout is blocked by budget review." in user_content
    assert "Acme 上线受预算审查阻塞。" in user_content
    assert "Can you confirm the Acme rollout still lands on Friday?" in user_content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "expected_env"),
    [
        ("qwen_api_key", "QWEN_API_KEY"),
        ("qwen_base_url", "QWEN_BASE_URL"),
        ("qwen_final_model", "QWEN_FINAL_MODEL"),
    ],
)
async def test_qwen_final_provider_reports_missing_config_name_only(
    field_name: str,
    expected_env: str,
) -> None:
    settings = qwen_text_settings()
    setattr(settings, field_name, None)
    provider = QwenFinalTranslationProvider(settings=settings)

    with pytest.raises(FinalTranslationError, match=expected_env) as exc_info:
        await provider.translate_final(
            FinalTranslationRequest(sequence=1, text="We need to align."),
        )

    assert "test-qwen-key" not in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"error": {"code": "service_unavailable"}}),
        httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]}),
        httpx.Response(200, content=b"{not-json"),
    ],
)
async def test_qwen_final_provider_wraps_http_empty_and_json_failures(
    response: httpx.Response,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        provider = QwenFinalTranslationProvider(
            settings=qwen_text_settings(),
            http_client=http_client,
        )

        with pytest.raises(FinalTranslationError):
            await provider.translate_final(
                FinalTranslationRequest(sequence=1, text="We need to align."),
            )
