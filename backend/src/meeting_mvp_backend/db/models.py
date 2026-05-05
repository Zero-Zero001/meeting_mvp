from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meeting_mvp_backend.db.base import Base


def enum_values[EnumType: StrEnum](enum_type: type[EnumType]) -> list[str]:
    return [item.value for item in enum_type]


class SourcePlatform(StrEnum):
    GOOGLE_MEET = "google_meet"
    TEAMS_WEB = "teams_web"
    ZOOM_WEB = "zoom_web"
    TENCENT_MEETING_WEB = "tencent_meeting_web"
    UNKNOWN = "unknown"


class CaptureMode(StrEnum):
    TAB_AUDIO = "tab_audio"
    SYSTEM_AUDIO = "system_audio"


class MeetingSessionStatus(StrEnum):
    PENDING_AUDIO = "pending_audio"
    ACTIVE = "active"
    ENDED = "ended"
    QUOTA_STOPPED = "quota_stopped"
    ERROR = "error"


class TranslationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ExportFormat(StrEnum):
    MARKDOWN = "markdown"
    JSON = "json"


source_platform_enum = Enum(
    SourcePlatform,
    name="source_platform",
    values_callable=enum_values,
)
capture_mode_enum = Enum(
    CaptureMode,
    name="capture_mode",
    values_callable=enum_values,
)
meeting_session_status_enum = Enum(
    MeetingSessionStatus,
    name="meeting_session_status",
    values_callable=enum_values,
)
translation_status_enum = Enum(
    TranslationStatus,
    name="translation_status",
    values_callable=enum_values,
)
export_format_enum = Enum(
    ExportFormat,
    name="export_format",
    values_callable=enum_values,
)


class AnonymousClient(Base):
    __tablename__ = "anonymous_client"

    client_id: Mapped[str] = mapped_column(String(length=64), primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    daily_minutes_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_ip_hash: Mapped[str] = mapped_column(String(length=128), nullable=False)
    user_agent_hash: Mapped[str] = mapped_column(String(length=128), nullable=False)

    sessions: Mapped[list[MeetingSession]] = relationship(back_populates="client")
    usage_events: Mapped[list[UsageEvent]] = relationship(back_populates="client")


class MeetingSession(Base):
    __tablename__ = "meeting_session"
    __table_args__ = (
        Index("ix_meeting_session_client_id", "client_id"),
        Index("ix_meeting_session_retention_expires_at", "retention_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(
        ForeignKey("anonymous_client.client_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(length=255))
    source_platform: Mapped[SourcePlatform] = mapped_column(
        source_platform_enum,
        nullable=False,
        default=SourcePlatform.UNKNOWN,
        server_default=SourcePlatform.UNKNOWN.value,
    )
    capture_mode: Mapped[CaptureMode] = mapped_column(
        capture_mode_enum,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    status: Mapped[MeetingSessionStatus] = mapped_column(
        meeting_session_status_enum,
        nullable=False,
        default=MeetingSessionStatus.PENDING_AUDIO,
        server_default=MeetingSessionStatus.PENDING_AUDIO.value,
    )
    quota_seconds_consumed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    archive_token_hash: Mapped[str] = mapped_column(String(length=255), nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    client: Mapped[AnonymousClient] = relationship(back_populates="sessions")
    transcript_segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    usage_events: Mapped[list[UsageEvent]] = relationship(back_populates="session")
    export_files: Mapped[list[ExportFile]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segment"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence",
            name="uq_transcript_segment_session_id_sequence",
        ),
        Index("ix_transcript_segment_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meeting_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    english_text_final: Mapped[str] = mapped_column(Text, nullable=False)
    chinese_text_final: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_label: Mapped[str | None] = mapped_column(String(length=128))
    is_key_sentence: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    asr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    translation_status: Mapped[TranslationStatus] = mapped_column(
        translation_status_enum,
        nullable=False,
        default=TranslationStatus.COMPLETED,
        server_default=TranslationStatus.COMPLETED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped[MeetingSession] = relationship(back_populates="transcript_segments")


class UsageEvent(Base):
    __tablename__ = "usage_event"
    __table_args__ = (
        Index("ix_usage_event_client_id", "client_id"),
        Index("ix_usage_event_session_id", "session_id"),
        Index("ix_usage_event_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(
        ForeignKey("anonymous_client.client_id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("meeting_session.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(length=128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    client: Mapped[AnonymousClient] = relationship(back_populates="usage_events")
    session: Mapped[MeetingSession | None] = relationship(back_populates="usage_events")


class ExportFile(Base):
    __tablename__ = "export_file"
    __table_args__ = (
        Index("ix_export_file_session_id", "session_id"),
        Index("ix_export_file_retention_expires_at", "retention_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meeting_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[ExportFormat] = mapped_column(export_format_enum, nullable=False)
    cos_object_key: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    cos_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    session: Mapped[MeetingSession] = relationship(back_populates="export_files")
