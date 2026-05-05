from pathlib import Path

import pytest

from meeting_mvp_backend.config import (
    AppEnv,
    SettingsError,
    load_settings,
    settings_status,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]

SETTINGS_ENV_NAMES = [
    "APP_ENV",
    "APP_TIMEZONE",
    "PUBLIC_BASE_URL",
    "API_BASE_URL",
    "WS_BASE_URL",
    "LOG_LEVEL",
    "DATABASE_URL",
    "REDIS_URL",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "DAILY_FREE_SECONDS",
    "SESSION_MAX_SECONDS",
    "MAX_ACTIVE_SESSIONS_PER_CLIENT",
    "MONTHLY_BUDGET_RMB",
    "BUDGET_FUSE_RMB",
    "ARCHIVE_RETENTION_DAYS",
    "COS_SIGNED_URL_TTL_SECONDS",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_STT_LOCATION",
    "GOOGLE_STT_RECOGNIZER",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_INTERIM_MODEL",
    "QWEN_INTERIM_ENABLED",
    "QWEN_FINAL_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_FINAL_MODEL",
    "OPENAI_STT_ENABLED",
    "OPENAI_STT_MODEL",
    "TENCENT_COS_SECRET_ID",
    "TENCENT_COS_SECRET_KEY",
    "TENCENT_COS_REGION",
    "TENCENT_COS_BUCKET",
    "TENCENT_COS_EXPORT_PREFIX",
    "MEETING_MVP_ENV_FILE",
]


def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTINGS_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_example_config_loads_local_mock_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)

    settings = load_settings(env_file=BACKEND_DIR / ".env.example")

    assert settings.app_env is AppEnv.LOCAL
    assert settings.archive_retention_days == 30
    assert settings.cos_signed_url_ttl_seconds == 3600
    assert settings.qwen_final_model == "qwen3.6-max-preview"
    assert settings.openai_stt_enabled is False


def test_production_config_reports_missing_required_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    for name in [
        "DATABASE_URL",
        "REDIS_URL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "QWEN_API_KEY",
        "TENCENT_COS_SECRET_KEY",
    ]:
        assert name in message


def test_settings_status_redacts_values(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("QWEN_API_KEY", "super-secret-qwen-value")

    settings = load_settings(env_file=BACKEND_DIR / ".env.example")
    status = settings_status(settings)

    assert status["QWEN_API_KEY"] == "set"
    assert "super-secret-qwen-value" not in repr(status)


def test_openai_stt_settings_required_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    for name in [
        "DATABASE_URL",
        "REDIS_URL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_STT_LOCATION",
        "GOOGLE_STT_RECOGNIZER",
        "QWEN_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_INTERIM_MODEL",
        "QWEN_FINAL_MODEL",
        "TENCENT_COS_SECRET_ID",
        "TENCENT_COS_SECRET_KEY",
        "TENCENT_COS_REGION",
        "TENCENT_COS_BUCKET",
        "TENCENT_COS_EXPORT_PREFIX",
    ]:
        monkeypatch.setenv(name, f"placeholder-{name.lower()}")
    monkeypatch.setenv("OPENAI_STT_ENABLED", "true")

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "OPENAI_API_KEY" in message
    assert "OPENAI_STT_MODEL" in message
