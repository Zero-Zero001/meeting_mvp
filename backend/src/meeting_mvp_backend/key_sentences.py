from __future__ import annotations

_ENGLISH_KEY_PHRASES = (
    "action item",
    "align on",
    "before friday",
    "blocker",
    "budget",
    "by tomorrow",
    "confirm",
    "customer escalation",
    "deadline",
    "decision",
    "follow up",
    "launch",
    "must",
    "need to",
    "owner",
    "risk",
)
_CHINESE_KEY_PHRASES = (
    "行动项",
    "必须",
    "负责人",
    "风险",
    "跟进",
    "决定",
    "截止",
    "确认",
    "客户升级",
    "上线",
    "预算",
    "需要",
    "周五",
)


def is_key_sentence_candidate(
    *,
    english_text_final: str,
    chinese_text_final: str,
) -> bool:
    normalized_english = _normalize_text(english_text_final)
    normalized_chinese = chinese_text_final.strip()
    return any(phrase in normalized_english for phrase in _ENGLISH_KEY_PHRASES) or any(
        phrase in normalized_chinese for phrase in _CHINESE_KEY_PHRASES
    )


def key_sentence_display_text(
    *,
    english_text_final: str,
    chinese_text_final: str,
) -> str:
    chinese = chinese_text_final.strip()
    if chinese:
        return chinese
    return english_text_final.strip()


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())
