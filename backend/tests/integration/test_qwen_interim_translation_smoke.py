from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.translation_providers import QwenInterimTranslationProvider

pytestmark = pytest.mark.integration

RUN_QWEN_INTERIM_SMOKE = "RUN_QWEN_INTERIM_SMOKE"
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


@pytest.mark.asyncio
async def test_qwen_interim_translation_smoke_returns_chinese_text() -> None:
    settings = _require_smoke_settings()
    provider = QwenInterimTranslationProvider(settings=settings)
    try:
        translated = await provider.translate_interim(
            "We need to align on the launch timeline before Friday.",
        )
    finally:
        await provider.close()

    assert translated.strip() != ""
    assert CJK_PATTERN.search(translated) is not None
    assert "We need to align" not in translated


def _require_smoke_settings() -> Settings:
    if _env_value(RUN_QWEN_INTERIM_SMOKE) not in {"1", "true", "TRUE", "yes", "YES"}:
        pytest.skip(
            f"set {RUN_QWEN_INTERIM_SMOKE}=1 to run real Qwen interim smoke tests",
        )

    settings = _load_settings_from_env()
    missing_names = [
        name
        for name, value in {
            "QWEN_API_KEY": settings.qwen_api_key,
            "QWEN_BASE_URL": settings.qwen_base_url,
            "QWEN_INTERIM_MODEL": settings.qwen_interim_model,
        }.items()
        if value is None or value.strip() == ""
    ]
    if missing_names:
        pytest.skip("missing Qwen interim smoke env: " + ", ".join(missing_names))
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
