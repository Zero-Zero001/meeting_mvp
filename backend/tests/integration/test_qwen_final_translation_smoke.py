from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.translation_providers import (
    FinalTranslationContextSegment,
    FinalTranslationRequest,
    QwenFinalTranslationProvider,
)

pytestmark = pytest.mark.integration

RUN_QWEN_FINAL_SMOKE = "RUN_QWEN_FINAL_SMOKE"
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


@pytest.mark.asyncio
async def test_qwen_final_translation_smoke_returns_contextual_chinese_text() -> None:
    settings = _require_smoke_settings()
    provider = QwenFinalTranslationProvider(settings=settings)
    try:
        translated = await provider.translate_final(
            FinalTranslationRequest(
                sequence=3,
                text=(
                    "Please confirm that the Acme rollout is still planned for "
                    "Friday after the budget review."
                ),
                context=(
                    FinalTranslationContextSegment(
                        sequence=1,
                        english_text_final=(
                            "The Acme rollout is waiting for budget review."
                        ),
                        chinese_text_final="Acme 上线正在等待预算审查。",
                    ),
                    FinalTranslationContextSegment(
                        sequence=2,
                        english_text_final="Finance expects to finish tomorrow.",
                        chinese_text_final="财务预计明天完成。",
                    ),
                ),
            ),
        )
    finally:
        await provider.close()

    normalized = translated.strip()
    assert normalized != ""
    assert CJK_PATTERN.search(normalized) is not None
    assert "Please confirm" not in normalized
    assert "acme" in normalized.casefold()


def _require_smoke_settings() -> Settings:
    if _env_value(RUN_QWEN_FINAL_SMOKE) not in {"1", "true", "TRUE", "yes", "YES"}:
        pytest.skip(f"set {RUN_QWEN_FINAL_SMOKE}=1 to run real Qwen final smoke tests")

    settings = _load_settings_from_env()
    missing_names = [
        name
        for name, value in {
            "QWEN_API_KEY": settings.qwen_api_key,
            "QWEN_BASE_URL": settings.qwen_base_url,
            "QWEN_FINAL_MODEL": settings.qwen_final_model,
        }.items()
        if value is None or value.strip() == ""
    ]
    if missing_names:
        pytest.skip("missing Qwen final smoke env: " + ", ".join(missing_names))
    return settings


def _load_settings_from_env() -> Settings:
    env_file = _env_value("MEETING_MVP_ENV_FILE")
    if env_file is None:
        return Settings()
    return Settings(_env_file=Path(env_file))  # type: ignore[call-arg]


def _env_value(name: str) -> str | None:
    direct = os.getenv(name)
    if direct is not None and direct != "":
        return direct

    env_file = os.getenv("MEETING_MVP_ENV_FILE")
    if not env_file:
        return None
    path = Path(env_file)
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'")
    return None
