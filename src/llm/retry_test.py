from __future__ import annotations

from src.llm.errors import (
    is_quota_exhausted,
    is_retryable_error,
)


class FakeError(Exception):
    pass


def main() -> None:

    gemini_quota = FakeError(
        "429 RESOURCE_EXHAUSTED "
        "Quota exceeded for metric: "
        "GenerateRequestsPerDayPerProject"
    )

    groq_tpd = FakeError(
        "Error code: 429 - "
        "Rate limit reached for model "
        "openai/gpt-oss-120b "
        "tokens per day (TPD): "
        "Limit 200000, Used 197906, "
        "Requested 2677"
    )

    groq_tpm = FakeError(
        "Error code: 429 - "
        "Rate limit reached for model "
        "openai/gpt-oss-120b "
        "tokens per minute (TPM): "
        "Limit 8000"
    )

    temporary_503 = FakeError(
        "503 Service Unavailable"
    )

    deepseek_balance = FakeError(
        "402 Insufficient Balance"
    )

    print("=" * 70)
    print("LLM ERROR CLASSIFICATION TEST")
    print("=" * 70)

    tests = [
        (
            "Gemini daily quota",
            gemini_quota,
            False,
        ),
        (
            "Groq TPD exhaustion",
            groq_tpd,
            False,
        ),
        (
            "Groq TPM rate limit",
            groq_tpm,
            True,
        ),
        (
            "Temporary 503",
            temporary_503,
            True,
        ),
        (
            "DeepSeek balance",
            deepseek_balance,
            False,
        ),
    ]

    for name, error, expected_retryable in tests:

        actual_retryable = (
            is_retryable_error(error)
        )

        print()
        print(name)
        print(
            "  quota exhausted =",
            is_quota_exhausted(error),
        )
        print(
            "  retryable       =",
            actual_retryable,
        )
        print(
            "  expected        =",
            expected_retryable,
        )

        assert (
            actual_retryable
            == expected_retryable
        ), (
            f"{name}: expected "
            f"{expected_retryable}, got "
            f"{actual_retryable}"
        )

    print()
    print("=" * 70)
    print("ALL ERROR CLASSIFICATION TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()