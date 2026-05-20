from __future__ import annotations

from typing import Annotated, Literal, TypeGuard

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

type NonNegativeInt = Annotated[int, Field(ge=0)]
type AudioLevel = Annotated[float, Field(ge=0.0, le=1.0)]
type Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
type AudioChunkFrame = bytes | bytearray | memoryview
type ProviderStatusValue = Literal[
    "enabled",
    "disabled",
    "local_mock",
    "unconfigured",
]


class WireMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AudioFormat(WireMessage):
    sample_rate_hz: Literal[16000]
    channels: Literal[1]
    encoding: Literal["pcm16"]


class ProviderStatus(WireMessage):
    qwen_realtime_asr: ProviderStatusValue
    qwen_interim_translation: ProviderStatusValue
    qwen_final_translation: ProviderStatusValue


class SessionStartMessage(WireMessage):
    type: Literal["session_start"]
    client_id: str
    capture_mode: Literal["tab_audio", "system_audio"]
    source_platform: Literal[
        "google_meet",
        "teams_web",
        "zoom_web",
        "tencent_meeting_web",
        "unknown",
    ]
    audio_format: AudioFormat


class SessionResumeMessage(WireMessage):
    type: Literal["session_resume"]
    client_id: str
    session_id: str
    archive_token: str
    audio_format: AudioFormat


class HeartbeatMessage(WireMessage):
    type: Literal["heartbeat"]
    session_id: str


class SessionStopMessage(WireMessage):
    type: Literal["session_stop"]
    session_id: str


class SessionStartedMessage(WireMessage):
    type: Literal["session_started"]
    session_id: str
    archive_token: str
    archive_url: str
    provider_status: ProviderStatus
    remaining_seconds_today: NonNegativeInt


class SessionResumedMessage(WireMessage):
    type: Literal["session_resumed"]
    session_id: str
    archive_url: str
    remaining_seconds_today: NonNegativeInt


class QuotaUpdateMessage(WireMessage):
    type: Literal["quota_update"]
    remaining_seconds_today: NonNegativeInt


class AudioStatusMessage(WireMessage):
    type: Literal["audio_status"]
    has_audio: bool
    level: AudioLevel | None = None


class AsrInterimMessage(WireMessage):
    type: Literal["asr_interim"]
    text: str


class AsrFinalMessage(WireMessage):
    type: Literal["asr_final"]
    sequence: NonNegativeInt
    start_ms: NonNegativeInt
    end_ms: NonNegativeInt
    text: str
    confidence: Confidence | None = None


class TranslationInterimMessage(WireMessage):
    type: Literal["translation_interim"]
    text: str


class SegmentFinalMessage(WireMessage):
    type: Literal["segment_final"]
    segment_id: str
    sequence: NonNegativeInt
    start_ms: NonNegativeInt
    end_ms: NonNegativeInt
    english_text_final: str
    chinese_text_final: str


class KeySentenceUpdateMessage(WireMessage):
    type: Literal["key_sentence_update"]
    text: str


class TimelineItem(WireMessage):
    id: str
    item_type: str
    timestamp_ms: NonNegativeInt
    text: str
    segment_id: str | None = None


class TimelineUpdateMessage(WireMessage):
    type: Literal["timeline_update"]
    items: list[TimelineItem]


class WarningMessage(WireMessage):
    type: Literal["warning"]
    code: str
    message: str | None = None


class ErrorMessage(WireMessage):
    type: Literal["error"]
    code: str
    message: str | None = None


class SessionClosedMessage(WireMessage):
    type: Literal["session_closed"]
    reason: str


type ClientMessage = Annotated[
    SessionStartMessage | SessionResumeMessage | HeartbeatMessage | SessionStopMessage,
    Field(discriminator="type"),
]

type ServerMessage = Annotated[
    SessionStartedMessage
    | SessionResumedMessage
    | QuotaUpdateMessage
    | AudioStatusMessage
    | AsrInterimMessage
    | AsrFinalMessage
    | TranslationInterimMessage
    | SegmentFinalMessage
    | KeySentenceUpdateMessage
    | TimelineUpdateMessage
    | WarningMessage
    | ErrorMessage
    | SessionClosedMessage,
    Field(discriminator="type"),
]

_CLIENT_MESSAGE_ADAPTER: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
_SERVER_MESSAGE_ADAPTER: TypeAdapter[ServerMessage] = TypeAdapter(ServerMessage)


def parse_client_message(payload: object) -> ClientMessage:
    return _CLIENT_MESSAGE_ADAPTER.validate_python(payload)


def parse_server_message(payload: object) -> ServerMessage:
    return _SERVER_MESSAGE_ADAPTER.validate_python(payload)


def is_audio_chunk_frame(payload: object) -> TypeGuard[AudioChunkFrame]:
    return isinstance(payload, (bytes, bytearray, memoryview))
