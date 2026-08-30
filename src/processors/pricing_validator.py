from __future__ import annotations

import re

from src.models.pricing_extraction import PricingModel


FREE_PATTERNS = [
    r"\bfree\b",
    r"\bfree plan\b",
    r"\bfree tier\b",
    r"\bfree forever\b",
    r"\bno cost\b",
]

PAID_PATTERNS = [
    r"\$\s*\d+",
    r"€\s*\d+",
    r"£\s*\d+",
    r"\bper month\b",
    r"\bper year\b",
    r"\bmonthly\b",
    r"\bannually\b",
    r"\bpaid plan\b",
    r"\bpaid tier\b",
]

ENTERPRISE_PATTERNS = [
    r"\benterprise plan\b",
    r"\benterprise tier\b",
    r"\benterprise pricing\b",
    r"\bcontact sales\b",
]


def contains_pattern(
    text: str,
    patterns: list[str],
) -> bool:
    normalized = text.lower()

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


def infer_pricing_model(
    pricing_text: str,
) -> PricingModel:
    """
    Deterministically infer pricing model from
    explicit pricing evidence.

    Returns UNKNOWN when evidence is insufficient.
    """

    if not pricing_text.strip():
        return PricingModel.UNKNOWN

    has_free = contains_pattern(
        pricing_text,
        FREE_PATTERNS,
    )

    has_paid = contains_pattern(
        pricing_text,
        PAID_PATTERNS,
    )

    has_enterprise = contains_pattern(
        pricing_text,
        ENTERPRISE_PATTERNS,
    )

    # Strongest classification:
    # free + paid => freemium
    if has_free and has_paid:
        return PricingModel.FREEMIUM

    # Explicit enterprise offering
    if has_enterprise:
        return PricingModel.ENTERPRISE

    # Paid-only evidence
    if has_paid and not has_free:
        return PricingModel.PAID

    # Free-only evidence
    if has_free and not has_paid:
        return PricingModel.FREE

    return PricingModel.UNKNOWN


def validate_pricing_model(
    model: PricingModel,
    pricing_text: str,
) -> PricingModel:
    """
    Validate an LLM-derived pricing model against
    deterministic page evidence.

    Deterministic evidence takes priority.
    """

    inferred_model = infer_pricing_model(
        pricing_text
    )

    if (
        inferred_model
        != PricingModel.UNKNOWN
    ):
        return inferred_model

    # No strong deterministic evidence.
    # Do not trust a weak LLM guess.
    return PricingModel.UNKNOWN