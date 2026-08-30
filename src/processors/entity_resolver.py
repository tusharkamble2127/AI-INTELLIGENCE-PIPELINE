from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable


CANONICAL_ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Google DeepMind",
    "Google",
    "Microsoft",
    "Meta",
    "NVIDIA",
    "Amazon",
    "xAI",
    "Mistral AI",
    "Cohere",
    "Hugging Face",
    "Stability AI",
    "Perplexity",
    "Scale AI",
    "Runway",
    "Character AI",
    "Databricks",
    "Snowflake",
    "Palantir",
    "AI21 Labs",
    "Replicate",
    "Together AI",
    "Groq",
    "Cerebras",
    "DeepL",
    "Weights & Biases",
    "ElevenLabs",
    "Midjourney",
    "Cursor",
    "Jasper",
    "Writer",
    "Glean",
    "Adept AI",
    "Inflection AI",
    "Sakana AI",
    "Figure AI",
    "H2O.ai",
    "DataRobot",
    "SambaNova Systems",
    "Aleph Alpha",
    "Stability",
    "AssemblyAI",
    "Pinecone",
    "LangChain",
    "Luma AI",
    "Vercel",
]


# NOTE:
# "ai" is intentionally NOT a removable company suffix.
# Otherwise "Open AI" incorrectly becomes "Open".
COMPANY_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
    "gmbh",
}


def normalize_name(
    name: str,
) -> str:
    """
    Normalize organization names while preserving
    meaningful tokens such as 'AI'.
    """

    if not name:
        return ""

    value = name.strip().lower()

    value = re.sub(
        r"[&+]",
        " and ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value,
    )

    value = " ".join(
        value.split()
    )

    tokens = value.split()

    # Remove only legal/business suffixes.
    while (
        tokens
        and tokens[-1]
        in COMPANY_SUFFIXES
    ):
        tokens.pop()

    return " ".join(tokens)


def compact_name(
    name: str,
) -> str:
    """
    Remove whitespace after normalization.

    Open AI -> openai
    OpenAI -> openai
    """

    normalized = normalize_name(
        name
    )

    return re.sub(
        r"\s+",
        "",
        normalized,
    )


def similarity(
    left: str,
    right: str,
) -> float:

    return SequenceMatcher(
        None,
        compact_name(left),
        compact_name(right),
    ).ratio()


def title_case_entity(
    name: str,
) -> str:
    """
    Produce a deterministic fallback canonical form.

    This is used only when the entity is not present
    in the seed list.
    """

    normalized = normalize_name(
        name
    )

    if not normalized:
        return name.strip()

    tokens = normalized.split()

    result: list[str] = []

    for token in tokens:

        if token in {
            "ai",
            "ml",
            "nlp",
            "llm",
            "api",
            "gpu",
            "saas",
        }:
            result.append(
                token.upper()
            )
        else:
            result.append(
                token.capitalize()
            )

    return " ".join(result)


def resolve_entity(
    raw_name: str,
    threshold: float = 0.88,
) -> tuple[str, float, str]:
    """
    Resolution order:

    1. Exact normalized seed match
    2. Compact seed match
    3. Fuzzy seed match
    4. Deterministic self-canonicalization

    The fourth path prevents valid entities outside the
    small seed list from being discarded.
    """

    if not raw_name.strip():
        return (
            raw_name,
            0.0,
            "EMPTY",
        )

    normalized_raw = normalize_name(
        raw_name
    )

    compact_raw = compact_name(
        raw_name
    )

    # -----------------------------------------------------
    # 1. Exact normalized seed match
    # -----------------------------------------------------

    for canonical in CANONICAL_ENTITIES:

        if (
            normalized_raw
            == normalize_name(
                canonical
            )
        ):
            return (
                canonical,
                1.0,
                "NORMALIZED_EXACT",
            )

    # -----------------------------------------------------
    # 2. Exact compact seed match
    # -----------------------------------------------------

    for canonical in CANONICAL_ENTITIES:

        if (
            compact_raw
            == compact_name(
                canonical
            )
        ):
            return (
                canonical,
                0.97,
                "COMPACT_EXACT",
            )

    # -----------------------------------------------------
    # 3. Fuzzy seed match
    # -----------------------------------------------------

    best_name = raw_name.strip()
    best_score = 0.0

    for canonical in CANONICAL_ENTITIES:

        score = similarity(
            raw_name,
            canonical,
        )

        if score > best_score:

            best_score = score
            best_name = canonical

    if best_score >= threshold:

        return (
            best_name,
            round(
                best_score,
                4,
            ),
            "FUZZY",
        )

    # -----------------------------------------------------
    # 4. Deterministic fallback
    # -----------------------------------------------------

    canonicalized = (
        title_case_entity(
            raw_name
        )
    )

    return (
        canonicalized,
        0.80,
        "SELF_CANONICALIZED",
    )


def resolve_many(
    names: Iterable[str],
) -> list[dict[str, object]]:

    results: list[
        dict[str, object]
    ] = []

    for raw_name in names:

        (
            canonical,
            confidence,
            method,
        ) = resolve_entity(
            raw_name
        )

        results.append(
            {
                "rawName": raw_name,
                "canonicalName": canonical,
                "confidence": round(
                    confidence,
                    4,
                ),
                "method": method,
            }
        )

    return results