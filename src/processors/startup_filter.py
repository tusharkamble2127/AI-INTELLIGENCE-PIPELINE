from __future__ import annotations

import re
from typing import Any


STRONG_SIGNALS = {
    "artificial intelligence": 3,
    "machine learning": 3,
    "deep learning": 3,
    "generative ai": 3,
    "large language model": 3,
    "llm": 3,
    "nlp": 3,
    "natural language processing": 3,
    "computer vision": 3,
    "ai agent": 3,
    "foundation model": 3,
    "multimodal": 3,
}

WEAK_SIGNALS = {
    "robotics": 1,
    "automation": 1,
    "autonomous": 1,
    "prediction": 1,
    "intelligent": 1,
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        value = " ".join(
            str(item)
            for item in value
        )

    text = str(value).lower()

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def build_search_text(
    company: dict[str, Any],
) -> str:

    fields = [
        company.get("industry"),
        company.get("subindustry"),
        company.get("industries"),
        company.get("tags"),
        company.get("one_liner"),
        company.get("long_description"),
    ]

    return normalize_text(fields)


def calculate_ai_score(
    company: dict[str, Any],
) -> tuple[int, list[str]]:

    text = build_search_text(company)

    score = 0
    matched_signals: list[str] = []

    for signal, weight in STRONG_SIGNALS.items():

        if signal in text:
            score += weight
            matched_signals.append(signal)

    for signal, weight in WEAK_SIGNALS.items():

        if signal in text:
            score += weight
            matched_signals.append(signal)

    return score, matched_signals


def is_ai_startup(
    company: dict[str, Any],
    minimum_score: int = 3,
) -> bool:

    score, _ = calculate_ai_score(company)

    return score >= minimum_score