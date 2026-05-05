"""create initial meeting mvp schema

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260505_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_platform = postgresql.ENUM(
    "google_meet",
    "teams_web",
    "zoom_web",
    "tencent_meeting_web",
    "unknown",
    name="source_platform",
    create_type=False,
)
capture_mode = postgresql.ENUM(
    "tab_audio",
    "system_audio",
    name="capture_mode",
    create_type=False,
)
meeting_session_status = postgresql.ENUM(
    "pending_audio",
    "active",
    "ended",
    "quota_stopped",
    "error",
    name="meeting_session_status",
    create_type=False,
)
translation_status = postgresql.ENUM(
    "completed",
    "failed",
    "retrying",
    name="translation_status",
    create_type=False,
)
export_format = postgresql.ENUM(
    "markdown",
    "json",
    name="export_format",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    source_platform.create(bind, checkfirst=True)
    capture_mode.create(bind, checkfirst=True)
    meeting_session_status.create(bind, checkfirst=True)
    translation_status.create(bind, checkfirst=True)
    export_format.create(bind, checkfirst=True)

    op.create_table(
        "anonymous_client",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "daily_minutes_used",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("created_ip_hash", sa.String(length=128), nullable=False),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("client_id", name=op.f("pk_anonymous_client")),
    )
    op.create_table(
        "meeting_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "source_platform",
            source_platform,
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("capture_mode", capture_mode, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            meeting_session_status,
            server_default="pending_audio",
            nullable=False,
        ),
        sa.Column(
            "quota_seconds_consumed",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("archive_token_hash", sa.String(length=255), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["anonymous_client.client_id"],
            name=op.f("fk_meeting_session_client_id_anonymous_client"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meeting_session")),
    )
    op.create_index(
        "ix_meeting_session_client_id",
        "meeting_session",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_meeting_session_retention_expires_at",
        "meeting_session",
        ["retention_expires_at"],
        unique=False,
    )
    op.create_table(
        "transcript_segment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("english_text_final", sa.Text(), nullable=False),
        sa.Column("chinese_text_final", sa.Text(), nullable=False),
        sa.Column("speaker_label", sa.String(length=128), nullable=True),
        sa.Column(
            "is_key_sentence",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("asr_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "translation_status",
            translation_status,
            server_default="completed",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["meeting_session.id"],
            name=op.f("fk_transcript_segment_session_id_meeting_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transcript_segment")),
        sa.UniqueConstraint(
            "session_id",
            "sequence",
            name="uq_transcript_segment_session_id_sequence",
        ),
    )
    op.create_index(
        "ix_transcript_segment_session_id",
        "transcript_segment",
        ["session_id"],
        unique=False,
    )
    op.create_table(
        "usage_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["anonymous_client.client_id"],
            name=op.f("fk_usage_event_client_id_anonymous_client"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["meeting_session.id"],
            name=op.f("fk_usage_event_session_id_meeting_session"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_event")),
    )
    op.create_index(
        "ix_usage_event_client_id",
        "usage_event",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_usage_event_event_type",
        "usage_event",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_usage_event_session_id",
        "usage_event",
        ["session_id"],
        unique=False,
    )
    op.create_table(
        "export_file",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", export_format, nullable=False),
        sa.Column("cos_object_key", sa.String(length=1024), nullable=False),
        sa.Column("cos_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["meeting_session.id"],
            name=op.f("fk_export_file_session_id_meeting_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_file")),
    )
    op.create_index(
        "ix_export_file_retention_expires_at",
        "export_file",
        ["retention_expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_export_file_session_id",
        "export_file",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_export_file_session_id", table_name="export_file")
    op.drop_index("ix_export_file_retention_expires_at", table_name="export_file")
    op.drop_table("export_file")
    op.drop_index("ix_usage_event_session_id", table_name="usage_event")
    op.drop_index("ix_usage_event_event_type", table_name="usage_event")
    op.drop_index("ix_usage_event_client_id", table_name="usage_event")
    op.drop_table("usage_event")
    op.drop_index("ix_transcript_segment_session_id", table_name="transcript_segment")
    op.drop_table("transcript_segment")
    op.drop_index(
        "ix_meeting_session_retention_expires_at",
        table_name="meeting_session",
    )
    op.drop_index("ix_meeting_session_client_id", table_name="meeting_session")
    op.drop_table("meeting_session")
    op.drop_table("anonymous_client")

    bind = op.get_bind()
    export_format.drop(bind, checkfirst=True)
    translation_status.drop(bind, checkfirst=True)
    meeting_session_status.drop(bind, checkfirst=True)
    capture_mode.drop(bind, checkfirst=True)
    source_platform.drop(bind, checkfirst=True)
