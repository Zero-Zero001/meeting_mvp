from __future__ import annotations

import pytest

from meeting_mvp_backend.key_sentences import (
    is_key_sentence_candidate,
    key_sentence_display_text,
)


@pytest.mark.parametrize(
    ("english_text", "chinese_text"),
    [
        (
            "We need to align on the launch timeline before Friday.",
            "我们需要在周五前对齐上线时间线。",
        ),
        (
            "The owner must confirm the budget risk by tomorrow.",
            "负责人必须在明天前确认预算风险。",
        ),
        (
            "Action item: follow up with the customer escalation.",
            "行动项：跟进客户升级问题。",
        ),
    ],
)
def test_key_sentence_rules_detect_action_decision_and_deadline_language(
    english_text: str,
    chinese_text: str,
) -> None:
    assert (
        is_key_sentence_candidate(
            english_text_final=english_text,
            chinese_text_final=chinese_text,
        )
        is True
    )


def test_key_sentence_rules_ignore_neutral_meeting_fillers() -> None:
    assert (
        is_key_sentence_candidate(
            english_text_final="Thanks everyone, I can see the slides now.",
            chinese_text_final="谢谢大家，我现在能看到幻灯片了。",
        )
        is False
    )


def test_key_sentence_display_text_prefers_chinese_final() -> None:
    assert (
        key_sentence_display_text(
            english_text_final="We need to align on the launch timeline before Friday.",
            chinese_text_final=" 我们需要在周五前对齐上线时间线。 ",
        )
        == "我们需要在周五前对齐上线时间线。"
    )


def test_key_sentence_display_text_falls_back_to_english_when_chinese_empty() -> None:
    assert (
        key_sentence_display_text(
            english_text_final=(
                " We need to align on the launch timeline before Friday. "
            ),
            chinese_text_final=" ",
        )
        == "We need to align on the launch timeline before Friday."
    )
