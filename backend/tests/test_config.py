from pathlib import Path

import pytest

from meeting_mvp_backend.config import (
    AppEnv,
    Settings,
    SettingsError,
    load_settings,
    settings_status,
)
from meeting_mvp_backend.main import _should_start_translation_retry_worker

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
    "DASHBOARD_ADMIN_TOKEN",
    "DASHBOARD_QWEN_ASR_USD_PER_SECOND",
    "DASHBOARD_QWEN_TEXT_INPUT_USD_PER_1M_TOKENS",
    "DASHBOARD_QWEN_TEXT_OUTPUT_USD_PER_1M_TOKENS",
    "DASHBOARD_USD_TO_RMB",
    "ARCHIVE_RETENTION_DAYS",
    "COS_SIGNED_URL_TTL_SECONDS",
    "ASR_PROVIDER",
    "QWEN_ASR_ENABLED",
    "QWEN_ASR_MODEL",
    "QWEN_ASR_BASE_URL",
    "QWEN_ASR_SAMPLE_RATE_HZ",
    "QWEN_ASR_AUDIO_FORMAT",
    "QWEN_ASR_LANGUAGE",
    "SESSION_RESUME_GRACE_SECONDS",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_INTERIM_MODEL",
    "QWEN_INTERIM_ENABLED",
    "QWEN_FINAL_ENABLED",
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
    assert settings.dashboard_admin_token is None
    assert settings.dashboard_qwen_asr_usd_per_second == 0.00009
    assert settings.dashboard_qwen_text_input_usd_per_1m_tokens == 0.861
    assert settings.dashboard_qwen_text_output_usd_per_1m_tokens == 3.441
    assert settings.dashboard_usd_to_rmb == 7.2
    assert settings.asr_provider == "qwen_realtime"
    assert settings.qwen_asr_enabled is True
    assert settings.qwen_asr_model == "qwen3-asr-flash-realtime"
    assert settings.qwen_asr_sample_rate_hz == 16000
    assert settings.qwen_asr_audio_format == "pcm"
    assert settings.qwen_asr_language == "auto"
    assert settings.session_resume_grace_seconds == 30
    assert settings.qwen_interim_enabled is True
    assert settings.qwen_final_enabled is True
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
        "QWEN_API_KEY",
        "QWEN_ASR_BASE_URL",
        "QWEN_ASR_MODEL",
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
        "QWEN_API_KEY",
        "QWEN_BASE_URL",
        "QWEN_ASR_BASE_URL",
        "QWEN_ASR_MODEL",
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


def test_qwen_required_settings_follow_provider_switches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    for name, value in {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "https://meeting.example.test",
        "API_BASE_URL": "https://meeting.example.test/api",
        "WS_BASE_URL": "wss://meeting.example.test/ws",
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "TENCENT_COS_SECRET_ID": "placeholder-cos-secret-id",
        "TENCENT_COS_SECRET_KEY": "placeholder-cos-secret-key",
        "TENCENT_COS_REGION": "ap-guangzhou",
        "TENCENT_COS_BUCKET": "meeting-mvp-test",
        "TENCENT_COS_EXPORT_PREFIX": "exports/",
        "QWEN_ASR_ENABLED": "false",
        "QWEN_INTERIM_ENABLED": "false",
        "QWEN_FINAL_ENABLED": "false",
    }.items():
        monkeypatch.setenv(name, value)

    settings = load_settings()

    assert settings.app_env is AppEnv.PRODUCTION
    assert settings.qwen_asr_enabled is False
    assert settings.qwen_interim_enabled is False
    assert settings.qwen_final_enabled is False


def test_interim_and_final_switches_require_only_their_own_qwen_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_settings_env(monkeypatch)
    for name, value in {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "https://meeting.example.test",
        "API_BASE_URL": "https://meeting.example.test/api",
        "WS_BASE_URL": "wss://meeting.example.test/ws",
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "TENCENT_COS_SECRET_ID": "placeholder-cos-secret-id",
        "TENCENT_COS_SECRET_KEY": "placeholder-cos-secret-key",
        "TENCENT_COS_REGION": "ap-guangzhou",
        "TENCENT_COS_BUCKET": "meeting-mvp-test",
        "TENCENT_COS_EXPORT_PREFIX": "exports/",
        "QWEN_ASR_ENABLED": "false",
        "QWEN_INTERIM_ENABLED": "true",
        "QWEN_FINAL_ENABLED": "false",
    }.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(SettingsError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "QWEN_API_KEY" in message
    assert "QWEN_BASE_URL" in message
    assert "QWEN_INTERIM_MODEL" in message
    assert "QWEN_ASR_BASE_URL" not in message
    assert "QWEN_ASR_MODEL" not in message
    assert "QWEN_FINAL_MODEL" not in message


def test_translation_retry_worker_does_not_start_when_final_disabled() -> None:
    settings = Settings(
        app_env=AppEnv.PRODUCTION,
        database_url="postgresql+psycopg://user:pass@localhost/db",
        qwen_api_key="placeholder-qwen-api-key",
        qwen_base_url="https://dashscope.example.test/compatible-mode/v1",
        qwen_final_enabled=False,
        qwen_final_model="qwen3.6-max-preview",
        redis_url="redis://localhost:6379/0",
    )

    assert _should_start_translation_retry_worker(settings) is False
