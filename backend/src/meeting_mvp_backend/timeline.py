from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from meeting_mvp_backend.db.models import ExportFormat

type TimelineItemType = Literal[
    "segment_final",
    "key_sentence",
    "export_created",
    "exception",
]

_TIMELINE_TYPE_SORT_ORDER: dict[TimelineItemType, int] = {
    "segment_final": 0,
    "key_sentence": 1,
    "exception": 2,
    "export_created": 3,
}
_EXCEPTION_TEXT_BY_CODE = {
    "archive_export_failed": "归档导出失败",
    "budget_fuse_triggered": "预算保险丝已触发",
    "daily_quota_exhausted": "今日额度已用尽",
    "mock_qwen_interim_retry": "临时理解出现可恢复异常",
    "qwen_asr_error": "英文转写服务异常",
    "qwen_final_translation_failed": "中文正式翻译失败，已进入后台补译",
    "qwen_interim_translation_failed": "中文临时理解暂时不可用",
}


@dataclass(frozen=True, slots=True)
class TimelineItemRecord:
    id: str
    item_type: TimelineItemType
    timestamp_ms: int
    text: str
    segment_id: uuid.UUID | None = None


def build_segment_final_timeline_item(
    *,
    chinese_text_final: str,
    english_text_final: str,
    end_ms: int,
    segment_id: uuid.UUID,
) -> TimelineItemRecord:
    return TimelineItemRecord(
        id=f"segment-final-{segment_id}",
        item_type="segment_final",
        segment_id=segment_id,
        text=_timeline_display_text(
            chinese_text_final=chinese_text_final,
            english_text_final=english_text_final,
            fallback="Final 片段已归档",
        ),
        timestamp_ms=max(end_ms, 0),
    )


def build_key_sentence_timeline_item(
    *,
    chinese_text_final: str,
    english_text_final: str,
    end_ms: int,
    segment_id: uuid.UUID,
) -> TimelineItemRecord:
    return TimelineItemRecord(
        id=f"key-sentence-{segment_id}",
        item_type="key_sentence",
        segment_id=segment_id,
        text=_timeline_display_text(
            chinese_text_final=chinese_text_final,
            english_text_final=english_text_final,
            fallback="重点句已识别",
        ),
        timestamp_ms=max(end_ms, 0),
    )


def build_exception_timeline_item(
    *,
    code: str,
    occurrence_index: int,
    segment_id: uuid.UUID | None = None,
    timestamp_ms: int,
) -> TimelineItemRecord:
    return TimelineItemRecord(
        id=f"exception-{code}-{occurrence_index}",
        item_type="exception",
        segment_id=segment_id,
        text=exception_text_for_code(code),
        timestamp_ms=max(timestamp_ms, 0),
    )


def build_archive_exception_timeline_item(
    *,
    code: str,
    event_id: uuid.UUID,
    segment_id: uuid.UUID | None = None,
    timestamp_ms: int,
) -> TimelineItemRecord:
    return TimelineItemRecord(
        id=f"exception-{event_id}",
        item_type="exception",
        segment_id=segment_id,
        text=exception_text_for_code(code),
        timestamp_ms=max(timestamp_ms, 0),
    )


def build_export_created_timeline_item(
    *,
    export_format: ExportFormat,
    export_id: uuid.UUID,
    timestamp_ms: int,
) -> TimelineItemRecord:
    return TimelineItemRecord(
        id=f"export-created-{export_id}",
        item_type="export_created",
        text=f"已生成 {export_format_label(export_format)} 导出",
        timestamp_ms=max(timestamp_ms, 0),
    )


def export_format_label(export_format: ExportFormat) -> str:
    if export_format is ExportFormat.MARKDOWN:
        return "Markdown"
    return "JSON"


def exception_text_for_code(code: str) -> str:
    return _EXCEPTION_TEXT_BY_CODE.get(code, "会议出现异常")


def relative_timestamp_ms(
    *,
    created_at: datetime,
    session_duration_seconds: int,
    session_started_at: datetime | None,
) -> int:
    if session_started_at is None:
        return max(session_duration_seconds, 0) * 1000
    return max(int((created_at - session_started_at).total_seconds() * 1000), 0)


def sort_timeline_items(
    items: list[TimelineItemRecord],
) -> list[TimelineItemRecord]:
    return sorted(
        items,
        key=lambda item: (
            item.timestamp_ms,
            _TIMELINE_TYPE_SORT_ORDER[item.item_type],
            item.id,
        ),
    )


def _timeline_display_text(
    *,
    chinese_text_final: str,
    english_text_final: str,
    fallback: str,
) -> str:
    chinese_text = " ".join(chinese_text_final.split())
    if chinese_text:
        return chinese_text
    english_text = " ".join(english_text_final.split())
    if english_text:
        return english_text
    return fallback
