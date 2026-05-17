from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(RuntimeError):
    """Raised when deployment configuration is missing or invalid."""


class AppEnv(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


StatusValue = Literal["set", "unset"]
AsrProvider = Literal["qwen_realtime"]

BACKEND_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = BACKEND_ROOT.parent

ENV_FIELD_MAP = {
    "APP_ENV": "app_env",
    "APP_TIMEZONE": "app_timezone",
    "PUBLIC_BASE_URL": "public_base_url",
    "API_BASE_URL": "api_base_url",
    "WS_BASE_URL": "ws_base_url",
    "LOG_LEVEL": "log_level",
    "DATABASE_URL": "database_url",
    "REDIS_URL": "redis_url",
    "POSTGRES_DB": "postgres_db",
    "POSTGRES_USER": "postgres_user",
    "POSTGRES_PASSWORD": "postgres_password",
    "REDIS_PASSWORD": "redis_password",
    "DAILY_FREE_SECONDS": "daily_free_seconds",
    "SESSION_MAX_SECONDS": "session_max_seconds",
    "MAX_ACTIVE_SESSIONS_PER_CLIENT": "max_active_sessions_per_client",
    "MONTHLY_BUDGET_RMB": "monthly_budget_rmb",
    "BUDGET_FUSE_RMB": "budget_fuse_rmb",
    "DASHBOARD_ADMIN_TOKEN": "dashboard_admin_token",
    "DASHBOARD_QWEN_ASR_USD_PER_SECOND": "dashboard_qwen_asr_usd_per_second",
    "DASHBOARD_QWEN_TEXT_INPUT_USD_PER_1M_TOKENS": (
        "dashboard_qwen_text_input_usd_per_1m_tokens"
    ),
    "DASHBOARD_QWEN_TEXT_OUTPUT_USD_PER_1M_TOKENS": (
        "dashboard_qwen_text_output_usd_per_1m_tokens"
    ),
    "DASHBOARD_USD_TO_RMB": "dashboard_usd_to_rmb",
    "ARCHIVE_RETENTION_DAYS": "archive_retention_days",
    "COS_SIGNED_URL_TTL_SECONDS": "cos_signed_url_ttl_seconds",
    "SESSION_RESUME_GRACE_SECONDS": "session_resume_grace_seconds",
    "ASR_PROVIDER": "asr_provider",
    "QWEN_API_KEY": "qwen_api_key",
    "QWEN_BASE_URL": "qwen_base_url",
    "QWEN_ASR_MODEL": "qwen_asr_model",
    "QWEN_ASR_BASE_URL": "qwen_asr_base_url",
    "QWEN_ASR_SAMPLE_RATE_HZ": "qwen_asr_sample_rate_hz",
    "QWEN_ASR_AUDIO_FORMAT": "qwen_asr_audio_format",
    "QWEN_ASR_LANGUAGE": "qwen_asr_language",
    "QWEN_INTERIM_MODEL": "qwen_interim_model",
    "QWEN_INTERIM_ENABLED": "qwen_interim_enabled",
    "QWEN_FINAL_MODEL": "qwen_final_model",
    "OPENAI_API_KEY": "openai_api_key",
    "OPENAI_BASE_URL": "openai_base_url",
    "OPENAI_FINAL_MODEL": "openai_final_model",
    "OPENAI_STT_ENABLED": "openai_stt_enabled",
    "OPENAI_STT_MODEL": "openai_stt_model",
    "TENCENT_COS_SECRET_ID": "tencent_cos_secret_id",
    "TENCENT_COS_SECRET_KEY": "tencent_cos_secret_key",
    "TENCENT_COS_REGION": "tencent_cos_region",
    "TENCENT_COS_BUCKET": "tencent_cos_bucket",
    "TENCENT_COS_EXPORT_PREFIX": "tencent_cos_export_prefix",
}

PRODUCTION_REQUIRED_ENV_NAMES = (
    "PUBLIC_BASE_URL",
    "API_BASE_URL",
    "WS_BASE_URL",
    "DATABASE_URL",
    "REDIS_URL",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_ASR_MODEL",
    "QWEN_ASR_BASE_URL",
    "QWEN_INTERIM_MODEL",
    "QWEN_FINAL_MODEL",
    "TENCENT_COS_SECRET_ID",
    "TENCENT_COS_SECRET_KEY",
    "TENCENT_COS_REGION",
    "TENCENT_COS_BUCKET",
    "TENCENT_COS_EXPORT_PREFIX",
)

OPENAI_STT_REQUIRED_ENV_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_STT_MODEL",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = Field(default=AppEnv.LOCAL, validation_alias="APP_ENV")
    app_timezone: str = Field(default="Asia/Shanghai", validation_alias="APP_TIMEZONE")
    public_base_url: str | None = Field(
        default=None,
        validation_alias="PUBLIC_BASE_URL",
    )
    api_base_url: str | None = Field(default=None, validation_alias="API_BASE_URL")
    ws_base_url: str | None = Field(default=None, validation_alias="WS_BASE_URL")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")
    postgres_db: str | None = Field(default=None, validation_alias="POSTGRES_DB")
    postgres_user: str | None = Field(default=None, validation_alias="POSTGRES_USER")
    postgres_password: str | None = Field(
        default=None,
        validation_alias="POSTGRES_PASSWORD",
    )
    redis_password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")

    daily_free_seconds: int = Field(default=2400, validation_alias="DAILY_FREE_SECONDS")
    session_max_seconds: int = Field(
        default=1800,
        validation_alias="SESSION_MAX_SECONDS",
    )
    max_active_sessions_per_client: int = Field(
        default=1,
        validation_alias="MAX_ACTIVE_SESSIONS_PER_CLIENT",
    )
    monthly_budget_rmb: int = Field(default=500, validation_alias="MONTHLY_BUDGET_RMB")
    budget_fuse_rmb: int = Field(default=400, validation_alias="BUDGET_FUSE_RMB")
    dashboard_admin_token: str | None = Field(
        default=None,
        validation_alias="DASHBOARD_ADMIN_TOKEN",
    )
    dashboard_qwen_asr_usd_per_second: float = Field(
        default=0.00009,
        validation_alias="DASHBOARD_QWEN_ASR_USD_PER_SECOND",
    )
    dashboard_qwen_text_input_usd_per_1m_tokens: float = Field(
        default=0.861,
        validation_alias="DASHBOARD_QWEN_TEXT_INPUT_USD_PER_1M_TOKENS",
    )
    dashboard_qwen_text_output_usd_per_1m_tokens: float = Field(
        default=3.441,
        validation_alias="DASHBOARD_QWEN_TEXT_OUTPUT_USD_PER_1M_TOKENS",
    )
    dashboard_usd_to_rmb: float = Field(
        default=7.2,
        validation_alias="DASHBOARD_USD_TO_RMB",
    )
    archive_retention_days: int = Field(
        default=30,
        validation_alias="ARCHIVE_RETENTION_DAYS",
    )
    cos_signed_url_ttl_seconds: int = Field(
        default=3600,
        validation_alias="COS_SIGNED_URL_TTL_SECONDS",
    )
    session_resume_grace_seconds: int = Field(
        default=30,
        validation_alias="SESSION_RESUME_GRACE_SECONDS",
    )

    asr_provider: AsrProvider = Field(
        default="qwen_realtime",
        validation_alias="ASR_PROVIDER",
    )
    qwen_api_key: str | None = Field(default=None, validation_alias="QWEN_API_KEY")
    qwen_base_url: str | None = Field(default=None, validation_alias="QWEN_BASE_URL")
    qwen_asr_model: str | None = Field(
        default=None,
        validation_alias="QWEN_ASR_MODEL",
    )
    qwen_asr_base_url: str | None = Field(
        default=None,
        validation_alias="QWEN_ASR_BASE_URL",
    )
    qwen_asr_sample_rate_hz: int = Field(
        default=16000,
        validation_alias="QWEN_ASR_SAMPLE_RATE_HZ",
    )
    qwen_asr_audio_format: Literal["pcm", "pcm16"] = Field(
        default="pcm",
        validation_alias="QWEN_ASR_AUDIO_FORMAT",
    )
    qwen_asr_language: str = Field(
        default="auto",
        validation_alias="QWEN_ASR_LANGUAGE",
    )
    qwen_interim_model: str | None = Field(
        default=None,
        validation_alias="QWEN_INTERIM_MODEL",
    )
    qwen_interim_enabled: bool = Field(
        default=True,
        validation_alias="QWEN_INTERIM_ENABLED",
    )
    qwen_final_model: str = Field(
        default="qwen3.6-max-preview",
        validation_alias="QWEN_FINAL_MODEL",
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(
        default=None,
        validation_alias="OPENAI_BASE_URL",
    )
    openai_final_model: str | None = Field(
        default=None,
        validation_alias="OPENAI_FINAL_MODEL",
    )
    openai_stt_enabled: bool = Field(
        default=False,
        validation_alias="OPENAI_STT_ENABLED",
    )
    openai_stt_model: str | None = Field(
        default=None,
        validation_alias="OPENAI_STT_MODEL",
    )

    tencent_cos_secret_id: str | None = Field(
        default=None,
        validation_alias="TENCENT_COS_SECRET_ID",
    )
    tencent_cos_secret_key: str | None = Field(
        default=None,
        validation_alias="TENCENT_COS_SECRET_KEY",
    )
    tencent_cos_region: str | None = Field(
        default=None,
        validation_alias="TENCENT_COS_REGION",
    )
    tencent_cos_bucket: str | None = Field(
        default=None,
        validation_alias="TENCENT_COS_BUCKET",
    )
    tencent_cos_export_prefix: str | None = Field(
        default="exports/",
        validation_alias="TENCENT_COS_EXPORT_PREFIX",
    )

    @field_validator("dashboard_admin_token", mode="before")
    @classmethod
    def empty_dashboard_admin_token_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


def _is_set(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _resolve_env_file(env_file: str | Path | None) -> Path | None:
    raw_env_file = env_file or os.environ.get("MEETING_MVP_ENV_FILE")
    if raw_env_file is None:
        return None

    raw_path = Path(raw_env_file)
    candidates = [
        raw_path,
        BACKEND_ROOT / raw_path,
        WORKSPACE_ROOT / raw_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise SettingsError(f"Environment file not found: {raw_env_file}")


def _missing_required_names(settings: Settings) -> list[str]:
    required_names: list[str] = []

    if settings.app_env in {AppEnv.STAGING, AppEnv.PRODUCTION}:
        required_names.extend(PRODUCTION_REQUIRED_ENV_NAMES)

    if settings.openai_stt_enabled:
        required_names.extend(OPENAI_STT_REQUIRED_ENV_NAMES)

    return [
        name
        for name in required_names
        if not _is_set(getattr(settings, ENV_FIELD_MAP[name]))
    ]


def load_settings(env_file: str | Path | None = None) -> Settings:
    resolved_env_file = _resolve_env_file(env_file)
    try:
        settings = Settings(_env_file=resolved_env_file)  # type: ignore[call-arg]
    except ValidationError as exc:
        invalid_names = sorted({str(error["loc"][0]) for error in exc.errors()})
        raise SettingsError(
            "Invalid configuration for: " + ", ".join(invalid_names),
        ) from exc

    missing_names = _missing_required_names(settings)
    if missing_names:
        raise SettingsError(
            "Missing required configuration: " + ", ".join(sorted(missing_names)),
        )

    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def settings_status(settings: Settings) -> dict[str, StatusValue]:
    return {
        env_name: "set" if _is_set(getattr(settings, field_name)) else "unset"
        for env_name, field_name in ENV_FIELD_MAP.items()
    }
