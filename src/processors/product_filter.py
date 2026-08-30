from __future__ import annotations

from typing import Any


STRONG_AI_TOPICS = {
    "Artificial Intelligence",
    "AI Agents",
    "AI Infrastructure",
    "AI Coding Agents",
    "AI Chatbots",
    "LLMs",
    "AI Workflow Automation",
}


AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "llm",
    "agent",
    "generative ai",
    "computer vision",
    "automation",
}


def is_ai_product(
    product: dict[str, Any],
) -> bool:

    topics = {
        topic
        for edge in (
            product
            .get("topics", {})
            .get("edges", [])
        )
        for topic in [
            edge
            .get("node", {})
            .get("name")
        ]
        if topic
    }

    if topics.intersection(
        STRONG_AI_TOPICS
    ):
        return True

    searchable = " ".join(
        [
            str(product.get("name", "")),
            str(product.get("tagline", "")),
            " ".join(topics),
        ]
    ).lower()

    return any(
        keyword in searchable
        for keyword in AI_KEYWORDS
    )