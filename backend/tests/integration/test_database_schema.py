from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.engine import Connection

from meeting_mvp_backend.config import load_settings
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
from meeting_mvp_backend.db.session import create_engine, create_session_factory

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "anonymous_client",
    "meeting_session",
    "transcript_segment",
    "usage_event",
    "export_file",
}


def get_table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


@pytest.mark.asyncio
async def test_initial_schema_tables_exist_and_core_rows_round_trip() -> None:
    settings = load_settings()
    assert settings.database_url is not None

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    client_id = f"integration-{uuid.uuid4()}"
    retention_expires_at = datetime.now(UTC) + timedelta(days=30)

    try:
        async with engine.connect() as connection:
            table_names = await connection.run_sync(get_table_names)
        assert EXPECTED_TABLES <= table_names

        async with session_factory() as session:
            client = AnonymousClient(
                client_id=client_id,
                created_ip_hash="ip-hash",
                user_agent_hash="ua-hash",
            )
            meeting = MeetingSession(
                client=client,
                source_platform=SourcePlatform.GOOGLE_MEET,
                capture_mode=CaptureMode.TAB_AUDIO,
                status=MeetingSessionStatus.PENDING_AUDIO,
                archive_token_hash="archive-token-hash",
                retention_expires_at=retention_expires_at,
            )
            segment = TranscriptSegment(
                session=meeting,
                sequence=1,
                start_ms=0,
                end_ms=2500,
                english_text_final="We need to ship this safely.",
                chinese_text_final="我们需要稳妥地发布这个功能。",
                is_key_sentence=True,
                asr_confidence=Decimal("0.9500"),
                translation_status=TranslationStatus.COMPLETED,
            )
            usage_event = UsageEvent(
                client=client,
                session=meeting,
                event_type="segment_archived",
                payload={"segment_sequence": 1, "contains_secret": False},
            )
            export_file = ExportFile(
                session=meeting,
                format=ExportFormat.MARKDOWN,
                cos_object_key=f"exports/{meeting.id}.md",
                cos_url="https://example.invalid/signed-url",
                retention_expires_at=retention_expires_at,
            )
            session.add_all([client, meeting, segment, usage_event, export_file])
            await session.flush()
            meeting_id = meeting.id
            segment_id = segment.id
            export_file_id = export_file.id
            await session.commit()

        async with session_factory() as session:
            saved_meeting = await session.scalar(
                select(MeetingSession).where(MeetingSession.id == meeting_id),
            )
            saved_segment = await session.scalar(
                select(TranscriptSegment).where(TranscriptSegment.id == segment_id),
            )
            saved_event = await session.scalar(
                select(UsageEvent).where(UsageEvent.client_id == client_id),
            )
            saved_export = await session.scalar(
                select(ExportFile).where(ExportFile.id == export_file_id),
            )

        assert saved_meeting is not None
        assert saved_meeting.status is MeetingSessionStatus.PENDING_AUDIO
        assert saved_meeting.archive_token_hash == "archive-token-hash"
        assert saved_meeting.retention_expires_at is not None
        assert saved_segment is not None
        assert saved_segment.english_text_final == "We need to ship this safely."
        assert saved_segment.chinese_text_final == "我们需要稳妥地发布这个功能。"
        assert saved_event is not None
        assert saved_event.payload["contains_secret"] is False
        assert saved_export is not None
        assert saved_export.format is ExportFormat.MARKDOWN
        assert saved_export.cos_object_key.startswith("exports/")
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(AnonymousClient).where(AnonymousClient.client_id == client_id),
            )
            await session.commit()
        await engine.dispose()
