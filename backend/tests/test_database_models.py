from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql.selectable import FromClause

from meeting_mvp_backend.db.base import Base
from meeting_mvp_backend.db.models import (
    AnonymousClient,
    CaptureMode,
    ExportFile,
    ExportFormat,
    MeetingSession,
    MeetingSessionStatus,
    SourcePlatform,
    TranscriptSegment,
    TranslationStatus,
    UsageEvent,
)

EXPECTED_TABLES = {
    "anonymous_client",
    "meeting_session",
    "transcript_segment",
    "usage_event",
    "export_file",
}


def column_names(table: FromClause) -> set[str]:
    return set(table.c.keys())


def enum_values(column_type: object) -> set[str]:
    assert isinstance(column_type, SQLAlchemyEnum)
    return set(column_type.enums)


def test_metadata_contains_only_step_07_core_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_anonymous_client_columns_match_prd_contract() -> None:
    assert column_names(AnonymousClient.__table__) == {
        "client_id",
        "first_seen_at",
        "last_seen_at",
        "daily_minutes_used",
        "created_ip_hash",
        "user_agent_hash",
    }


def test_meeting_session_supports_pending_audio_archive_and_retention() -> None:
    table = MeetingSession.__table__

    assert {
        "id",
        "client_id",
        "title",
        "source_platform",
        "capture_mode",
        "started_at",
        "ended_at",
        "duration_seconds",
        "status",
        "quota_seconds_consumed",
        "archive_token_hash",
        "retention_expires_at",
    } <= column_names(table)
    assert "archive_token" not in column_names(table)
    assert MeetingSessionStatus.PENDING_AUDIO.value in enum_values(table.c.status.type)
    assert enum_values(table.c.source_platform.type) == {
        item.value for item in SourcePlatform
    }
    assert enum_values(table.c.capture_mode.type) == {
        item.value for item in CaptureMode
    }
    assert isinstance(table.c.id.type, UUID)


def test_transcript_segment_columns_match_final_archive_contract() -> None:
    table = TranscriptSegment.__table__

    assert {
        "id",
        "session_id",
        "sequence",
        "start_ms",
        "end_ms",
        "english_text_final",
        "chinese_text_final",
        "speaker_label",
        "is_key_sentence",
        "asr_confidence",
        "translation_status",
        "created_at",
    } <= column_names(table)
    assert enum_values(table.c.translation_status.type) == {
        item.value for item in TranslationStatus
    }
    assert isinstance(table.c.id.type, UUID)


def test_usage_event_uses_jsonb_payload_without_audio_or_secret_columns() -> None:
    table = UsageEvent.__table__

    assert column_names(table) == {
        "id",
        "client_id",
        "session_id",
        "event_type",
        "payload",
        "created_at",
    }
    assert isinstance(table.c.payload.type, JSONB)
    lower_columns = {name.lower() for name in column_names(table)}
    assert not any("secret" in name for name in lower_columns)
    assert not any("audio" in name for name in lower_columns)


def test_export_file_columns_match_cos_export_contract() -> None:
    table = ExportFile.__table__

    assert {
        "id",
        "session_id",
        "format",
        "cos_object_key",
        "cos_url",
        "created_at",
        "retention_expires_at",
    } <= column_names(table)
    assert enum_values(table.c.format.type) == {item.value for item in ExportFormat}
    assert isinstance(table.c.id.type, UUID)
