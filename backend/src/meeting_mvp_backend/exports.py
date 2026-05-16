from __future__ import annotations

import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.archives import (
    ArchiveAccessDenied,
    ArchiveRepository,
    ArchiveSessionRecord,
    ArchiveTranscriptSegmentRecord,
)
from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import ExportFile, ExportFormat, TranslationStatus
from meeting_mvp_backend.usage_events import (
    UsageEventRecorder,
    UsageEventType,
    record_usage_event_best_effort,
)

Clock = Callable[[], datetime]
UuidFactory = Callable[[], uuid.UUID]
_CHINESE_UNAVAILABLE = "中文 final 暂不可用"


class ArchiveExportEmpty(Exception):
    """Raised when an authorized archive has no final segments to export."""


class ArchiveExportUnavailable(Exception):
    """Raised when export generation or storage is temporarily unavailable."""


class ArchiveExportConfigurationError(ArchiveExportUnavailable):
    """Raised when COS export configuration is incomplete."""


class ArchiveExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: ExportFormat


class ArchiveExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: uuid.UUID
    session_id: uuid.UUID
    format: ExportFormat
    download_url: str
    download_url_expires_at: datetime
    retention_expires_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExportFileRecord:
    export_id: uuid.UUID
    session_id: uuid.UUID
    export_format: ExportFormat
    cos_object_key: str
    cos_url: str
    created_at: datetime
    retention_expires_at: datetime


class ArchiveObjectStorage(Protocol):
    async def upload_bytes(
        self,
        *,
        content: bytes,
        content_type: str,
        object_key: str,
    ) -> None: ...

    async def create_signed_download_url(
        self,
        *,
        expires_in_seconds: int,
        object_key: str,
    ) -> str: ...


class ExportFileRepository(Protocol):
    async def create_export_file(
        self,
        *,
        cos_object_key: str,
        cos_url: str,
        created_at: datetime,
        export_id: uuid.UUID,
        export_format: ExportFormat,
        retention_expires_at: datetime,
        session_id: uuid.UUID,
    ) -> ExportFileRecord: ...


class SQLAlchemyExportFileRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def create_export_file(
        self,
        *,
        cos_object_key: str,
        cos_url: str,
        created_at: datetime,
        export_id: uuid.UUID,
        export_format: ExportFormat,
        retention_expires_at: datetime,
        session_id: uuid.UUID,
    ) -> ExportFileRecord:
        async with self._session_factory() as session:
            session.add(
                ExportFile(
                    id=export_id,
                    session_id=session_id,
                    format=export_format,
                    cos_object_key=cos_object_key,
                    cos_url=cos_url,
                    created_at=created_at,
                    retention_expires_at=retention_expires_at,
                ),
            )
            await session.commit()
        return ExportFileRecord(
            cos_object_key=cos_object_key,
            cos_url=cos_url,
            created_at=created_at,
            export_id=export_id,
            export_format=export_format,
            retention_expires_at=retention_expires_at,
            session_id=session_id,
        )


class TencentCosArchiveObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        secret_id: str,
        secret_key: str,
    ) -> None:
        from qcloud_cos import CosConfig, CosS3Client  # type: ignore[import-untyped]

        config = CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
            Scheme="https",
        )
        self._bucket = bucket
        self._client = CosS3Client(config)

    async def upload_bytes(
        self,
        *,
        content: bytes,
        content_type: str,
        object_key: str,
    ) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Body=content,
            Key=object_key,
            ContentType=content_type,
        )

    async def create_signed_download_url(
        self,
        *,
        expires_in_seconds: int,
        object_key: str,
    ) -> str:
        return str(
            self._client.get_presigned_url(
                Bucket=self._bucket,
                Expired=expires_in_seconds,
                Key=object_key,
                Method="GET",
            ),
        )


class ArchiveExportService:
    def __init__(
        self,
        *,
        archive_repository: ArchiveRepository,
        export_prefix: str,
        export_repository: ExportFileRepository,
        signed_url_ttl_seconds: int,
        storage: ArchiveObjectStorage,
        clock: Clock | None = None,
        usage_event_recorder: UsageEventRecorder | None = None,
        uuid_factory: UuidFactory | None = None,
    ) -> None:
        self._archive_repository = archive_repository
        self._clock = clock or _now_utc
        self._export_prefix = export_prefix
        self._export_repository = export_repository
        self._signed_url_ttl_seconds = signed_url_ttl_seconds
        self._storage = storage
        self._usage_event_recorder = usage_event_recorder
        self._uuid_factory = uuid_factory or uuid.uuid4

    async def create_export(
        self,
        *,
        request: ArchiveExportRequest,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveExportResponse:
        session = await self._authorize_session(session_id=session_id, token=token)
        segments = sorted(
            await self._archive_repository.list_segments(session_id),
            key=lambda segment: segment.sequence,
        )
        if not segments:
            await self._record_failed_event(
                error_type=ArchiveExportEmpty.__name__,
                export_format=request.format,
                segment_count=0,
                session=session,
                stage="empty_archive",
            )
            raise ArchiveExportEmpty("archive has no exportable final segments")

        end_reason = (
            await self._archive_repository.latest_session_closed_reason(session_id)
        ) or session.status.value
        exported_at = self._clock()
        content, content_type = _render_export_content(
            end_reason=end_reason,
            export_format=request.format,
            exported_at=exported_at,
            segments=segments,
            session=session,
        )
        export_id = self._uuid_factory()
        object_key = build_export_object_key(
            export_format=request.format,
            export_id=export_id,
            export_prefix=self._export_prefix,
            session_id=session.session_id,
        )

        try:
            await self._storage.upload_bytes(
                content=content,
                content_type=content_type,
                object_key=object_key,
            )
        except Exception as exc:
            await self._record_failed_event(
                error_type=exc.__class__.__name__,
                export_format=request.format,
                segment_count=len(segments),
                session=session,
                stage="cos_upload",
            )
            raise ArchiveExportUnavailable("export temporarily unavailable") from exc

        try:
            download_url = await self._storage.create_signed_download_url(
                expires_in_seconds=self._signed_url_ttl_seconds,
                object_key=object_key,
            )
        except Exception as exc:
            await self._record_failed_event(
                error_type=exc.__class__.__name__,
                export_format=request.format,
                segment_count=len(segments),
                session=session,
                stage="signed_url",
            )
            raise ArchiveExportUnavailable("export temporarily unavailable") from exc

        try:
            record = await self._export_repository.create_export_file(
                cos_object_key=object_key,
                cos_url=download_url,
                created_at=exported_at,
                export_id=export_id,
                export_format=request.format,
                retention_expires_at=session.retention_expires_at,
                session_id=session.session_id,
            )
        except Exception as exc:
            await self._record_failed_event(
                error_type=exc.__class__.__name__,
                export_format=request.format,
                segment_count=len(segments),
                session=session,
                stage="database",
            )
            raise ArchiveExportUnavailable("export temporarily unavailable") from exc

        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=session.client_id,
            session_id=session.session_id,
            event_type=UsageEventType.EXPORT_CREATED,
            payload={
                "file_size_bytes": len(content),
                "format": request.format.value,
                "segment_count": len(segments),
                "signed_url_ttl_seconds": self._signed_url_ttl_seconds,
                "translation_failed_count": _translation_failed_count(segments),
            },
        )
        return ArchiveExportResponse(
            created_at=record.created_at,
            download_url=record.cos_url,
            download_url_expires_at=exported_at
            + timedelta(seconds=self._signed_url_ttl_seconds),
            export_id=record.export_id,
            format=record.export_format,
            retention_expires_at=record.retention_expires_at,
            session_id=record.session_id,
        )

    async def _authorize_session(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveSessionRecord:
        if token.strip() == "":
            raise ArchiveAccessDenied("archive not found or expired")
        session = await self._archive_repository.get_session(session_id)
        if session is None:
            raise ArchiveAccessDenied("archive not found or expired")
        if session.retention_expires_at <= self._clock():
            raise ArchiveAccessDenied("archive not found or expired")
        if not secrets.compare_digest(
            hash_archive_token(token),
            session.archive_token_hash,
        ):
            raise ArchiveAccessDenied("archive not found or expired")
        return session

    async def _record_failed_event(
        self,
        *,
        error_type: str,
        export_format: ExportFormat,
        segment_count: int,
        session: ArchiveSessionRecord,
        stage: str,
    ) -> None:
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=session.client_id,
            session_id=session.session_id,
            event_type=UsageEventType.EXPORT_FAILED,
            payload={
                "error_type": error_type,
                "format": export_format.value,
                "segment_count": segment_count,
                "stage": stage,
            },
        )


def create_tencent_cos_storage_from_settings(
    settings: Settings,
) -> TencentCosArchiveObjectStorage:
    return TencentCosArchiveObjectStorage(
        bucket=_required_cos_setting(
            settings.tencent_cos_bucket,
            "TENCENT_COS_BUCKET",
        ),
        region=_required_cos_setting(
            settings.tencent_cos_region,
            "TENCENT_COS_REGION",
        ),
        secret_id=_required_cos_setting(
            settings.tencent_cos_secret_id,
            "TENCENT_COS_SECRET_ID",
        ),
        secret_key=_required_cos_setting(
            settings.tencent_cos_secret_key,
            "TENCENT_COS_SECRET_KEY",
        ),
    )


def build_export_object_key(
    *,
    export_format: ExportFormat,
    export_id: uuid.UUID,
    export_prefix: str,
    session_id: uuid.UUID,
) -> str:
    extension = "md" if export_format is ExportFormat.MARKDOWN else "json"
    clean_prefix = export_prefix.strip("/")
    suffix = f"{session_id}/{export_id}.{extension}"
    if clean_prefix == "":
        return suffix
    return f"{clean_prefix}/{suffix}"


def render_archive_markdown(
    *,
    end_reason: str,
    exported_at: datetime,
    segments: list[ArchiveTranscriptSegmentRecord],
    session: ArchiveSessionRecord,
) -> str:
    ordered_segments = sorted(segments, key=lambda segment: segment.sequence)
    lines = [
        "# 会议归档",
        "",
        "## 会话信息",
        "",
        f"- 会话 ID：{session.session_id}",
        f"- 会议平台：{session.source_platform.value}",
        f"- 捕获模式：{session.capture_mode.value}",
        f"- 会话状态：{session.status.value}",
        f"- 结束原因：{end_reason}",
        f"- 开始时间：{_format_datetime(session.started_at)}",
        f"- 结束时间：{_format_datetime(session.ended_at)}",
        f"- 会议时长秒数：{session.duration_seconds}",
        f"- 已消耗额度秒数：{session.quota_seconds_consumed}",
        f"- 归档保留至：{_format_datetime(session.retention_expires_at)}",
        f"- 导出时间：{_format_datetime(exported_at)}",
        "",
        "## 双语片段",
        "",
    ]
    for segment in ordered_segments:
        chinese_text = segment.chinese_text_final or _CHINESE_UNAVAILABLE
        lines.extend(
            [
                f"### 片段 {segment.sequence}",
                "",
                f"- 时间：{_format_timestamp(segment.start_ms)} - "
                f"{_format_timestamp(segment.end_ms)}",
                f"- 说话人：{segment.speaker_label or '未知'}",
                f"- 翻译状态：{segment.translation_status.value}",
                f"- 重点句：{'是' if segment.is_key_sentence else '否'}",
                "",
                "**英文**",
                "",
                segment.english_text_final,
                "",
                "**中文**",
                "",
                chinese_text,
                "",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


def render_archive_json(
    *,
    end_reason: str,
    exported_at: datetime,
    segments: list[ArchiveTranscriptSegmentRecord],
    session: ArchiveSessionRecord,
) -> str:
    payload = {
        "exported_at": exported_at.isoformat(),
        "segments": [
            {
                "segment_id": str(segment.segment_id),
                "sequence": segment.sequence,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "speaker_label": segment.speaker_label,
                "english_text_final": segment.english_text_final,
                "chinese_text_final": segment.chinese_text_final
                or _CHINESE_UNAVAILABLE,
                "translation_status": segment.translation_status.value,
                "is_key_sentence": segment.is_key_sentence,
            }
            for segment in sorted(segments, key=lambda item: item.sequence)
        ],
        "session": {
            "session_id": str(session.session_id),
            "source_platform": session.source_platform.value,
            "capture_mode": session.capture_mode.value,
            "status": session.status.value,
            "end_reason": end_reason,
            "started_at": _format_datetime(session.started_at),
            "ended_at": _format_datetime(session.ended_at),
            "duration_seconds": session.duration_seconds,
            "quota_seconds_consumed": session.quota_seconds_consumed,
            "retention_expires_at": _format_datetime(session.retention_expires_at),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_export_content(
    *,
    end_reason: str,
    export_format: ExportFormat,
    exported_at: datetime,
    segments: list[ArchiveTranscriptSegmentRecord],
    session: ArchiveSessionRecord,
) -> tuple[bytes, str]:
    if export_format is ExportFormat.MARKDOWN:
        return (
            render_archive_markdown(
                end_reason=end_reason,
                exported_at=exported_at,
                segments=segments,
                session=session,
            ).encode("utf-8"),
            "text/markdown; charset=utf-8",
        )
    return (
        render_archive_json(
            end_reason=end_reason,
            exported_at=exported_at,
            segments=segments,
            session=session,
        ).encode("utf-8"),
        "application/json; charset=utf-8",
    )


def _format_timestamp(timestamp_ms: int) -> str:
    total_seconds = timestamp_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _translation_failed_count(
    segments: list[ArchiveTranscriptSegmentRecord],
) -> int:
    return sum(
        1
        for segment in segments
        if segment.translation_status is TranslationStatus.FAILED
    )


def _required_cos_setting(value: str | None, env_name: str) -> str:
    if value is None or value.strip() == "":
        raise ArchiveExportConfigurationError(f"{env_name} is required for exports")
    return value


def _now_utc() -> datetime:
    return datetime.now(UTC)
