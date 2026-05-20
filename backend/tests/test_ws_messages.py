from __future__ import annotations

import pytest
from pydantic import ValidationError

from meeting_mvp_backend.ws_messages import (
    AsrFinalMessage,
    AudioStatusMessage,
    SegmentFinalMessage,
    SessionResumedMessage,
    SessionResumeMessage,
    SessionStartedMessage,
    SessionStartMessage,
    TimelineUpdateMessage,
    WarningMessage,
    is_audio_chunk_frame,
    parse_client_message,
    parse_server_message,
)

VALID_AUDIO_FORMAT = {
    "sample_rate_hz": 16000,
    "channels": 1,
    "encoding": "pcm16",
}


def test_parses_session_start_message() -> None:
    message = parse_client_message(
        {
            "type": "session_start",
            "client_id": "77777777-7777-4777-8777-777777777777",
            "capture_mode": "tab_audio",
            "source_platform": "google_meet",
            "audio_format": VALID_AUDIO_FORMAT,
        },
    )

    assert isinstance(message, SessionStartMessage)
    assert message.client_id == "77777777-7777-4777-8777-777777777777"
    assert message.audio_format.sample_rate_hz == 16000


def test_rejects_session_start_with_non_pcm16_format() -> None:
    with pytest.raises(ValidationError):
        parse_client_message(
            {
                "type": "session_start",
                "client_id": "77777777-7777-4777-8777-777777777777",
                "capture_mode": "tab_audio",
                "source_platform": "google_meet",
                "audio_format": {
                    "sample_rate_hz": 48000,
                    "channels": 2,
                    "encoding": "opus",
                },
            },
        )


def test_rejects_client_message_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        parse_client_message(
            {
                "type": "session_start",
                "client_id": "77777777-7777-4777-8777-777777777777",
                "capture_mode": "tab_audio",
                "audio_format": VALID_AUDIO_FORMAT,
            },
        )


def test_rejects_unknown_client_message_type() -> None:
    with pytest.raises(ValidationError):
        parse_client_message({"type": "provider_start"})


def test_parses_session_resume_message() -> None:
    message = parse_client_message(
        {
            "type": "session_resume",
            "client_id": "77777777-7777-4777-8777-777777777777",
            "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "archive_token": "archive-token",
            "audio_format": VALID_AUDIO_FORMAT,
        },
    )

    assert isinstance(message, SessionResumeMessage)
    assert message.session_id == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert message.archive_token == "archive-token"


def test_rejects_session_resume_with_extra_fields() -> None:
    with pytest.raises(ValidationError):
        parse_client_message(
            {
                "type": "session_resume",
                "client_id": "77777777-7777-4777-8777-777777777777",
                "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "archive_token": "archive-token",
                "audio_format": VALID_AUDIO_FORMAT,
                "source_platform": "google_meet",
            },
        )


def test_identifies_binary_audio_chunk_frame() -> None:
    assert is_audio_chunk_frame(b"\x00\x01\x02\x03") is True
    assert is_audio_chunk_frame(bytearray(b"\x00\x01")) is True
    assert is_audio_chunk_frame({"type": "audio_chunk"}) is False


def test_parses_required_session_started_response_fields() -> None:
    message = parse_server_message(
        {
            "type": "session_started",
            "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "archive_token": "archive-token",
            "archive_url": (
                "/archive/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
                "?token=archive-token"
            ),
            "provider_status": {
                "qwen_final_translation": "enabled",
                "qwen_interim_translation": "disabled",
                "qwen_realtime_asr": "enabled",
            },
            "remaining_seconds_today": 1800,
        },
    )

    assert isinstance(message, SessionStartedMessage)
    assert message.provider_status.qwen_interim_translation == "disabled"
    assert message.remaining_seconds_today == 1800


def test_parses_session_resumed_response_fields() -> None:
    message = parse_server_message(
        {
            "type": "session_resumed",
            "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "archive_url": (
                "/archive/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
                "?token=archive-token"
            ),
            "remaining_seconds_today": 1800,
        },
    )

    assert isinstance(message, SessionResumedMessage)
    assert message.remaining_seconds_today == 1800


def test_parses_segment_final_response() -> None:
    message = parse_server_message(
        {
            "type": "segment_final",
            "segment_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "sequence": 1,
            "start_ms": 1200,
            "end_ms": 3600,
            "english_text_final": "We need to align on the timeline.",
            "chinese_text_final": "Timeline alignment translation.",
        },
    )

    assert isinstance(message, SegmentFinalMessage)
    assert message.sequence == 1
    assert message.english_text_final == "We need to align on the timeline."


def test_parses_asr_final_response() -> None:
    message = parse_server_message(
        {
            "type": "asr_final",
            "sequence": 1,
            "start_ms": 0,
            "end_ms": 2400,
            "text": "We need to align on the timeline.",
            "confidence": 0.92,
        },
    )

    assert isinstance(message, AsrFinalMessage)
    assert message.sequence == 1
    assert message.start_ms == 0
    assert message.end_ms == 2400
    assert message.text == "We need to align on the timeline."
    assert message.confidence == 0.92


def test_rejects_invalid_asr_final_confidence() -> None:
    with pytest.raises(ValidationError):
        parse_server_message(
            {
                "type": "asr_final",
                "sequence": 1,
                "start_ms": 0,
                "end_ms": 2400,
                "text": "We need to align on the timeline.",
                "confidence": 1.5,
            },
        )


def test_parses_nullable_optional_response_fields() -> None:
    audio_status = parse_server_message(
        {"type": "audio_status", "has_audio": False, "level": None},
    )
    warning = parse_server_message(
        {"type": "warning", "code": "quota_near_limit", "message": None},
    )
    timeline = parse_server_message(
        {
            "type": "timeline_update",
            "items": [
                {
                    "id": "timeline-1",
                    "item_type": "segment",
                    "timestamp_ms": 1200,
                    "text": "A final segment was created.",
                    "segment_id": None,
                },
            ],
        },
    )

    assert isinstance(audio_status, AudioStatusMessage)
    assert audio_status.level is None
    assert isinstance(warning, WarningMessage)
    assert warning.message is None
    assert isinstance(timeline, TimelineUpdateMessage)
    assert timeline.items[0].segment_id is None


def test_rejects_unknown_server_message_type() -> None:
    with pytest.raises(ValidationError):
        parse_server_message({"type": "provider_debug"})
