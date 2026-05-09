from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MockFinalSegment:
    sequence: int
    start_ms: int
    end_ms: int
    english_text_final: str
    chinese_text_final: str
    is_key_sentence: bool


@dataclass(frozen=True, slots=True)
class MockProviderScript:
    english_interim: str
    warning_code: str
    warning_message: str
    chinese_interim: str
    final_segment: MockFinalSegment


DEFAULT_MOCK_PROVIDER_SCRIPT = MockProviderScript(
    english_interim="We need to align on the launch timeline.",
    warning_code="mock_qwen_interim_retry",
    warning_message="Mock interim provider recovered after a simulated retry.",
    chinese_interim="我们需要对齐上线时间线。",
    final_segment=MockFinalSegment(
        sequence=1,
        start_ms=0,
        end_ms=3200,
        english_text_final="We need to align on the launch timeline before Friday.",
        chinese_text_final="我们需要在周五前对齐上线时间线。",
        is_key_sentence=True,
    ),
)
