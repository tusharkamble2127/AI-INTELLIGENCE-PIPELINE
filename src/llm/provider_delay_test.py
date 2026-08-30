from __future__ import annotations

from src.llm.provider_state import (
    extract_retry_seconds,
)


def main() -> None:
    print("=" * 70)
    print("PROVIDER RETRY DELAY TEST")
    print("=" * 70)

    test_cases = [
        (
            "Groq minute + seconds",
            Exception(
                "Rate limit reached. "
                "Please try again in 1m49.296s."
            ),
            300,
        ),
        (
            "Gemini seconds",
            Exception(
                "Quota exceeded. "
                "Please retry in 44s."
            ),
            300,
        ),
        (
            "Provider seconds below minimum",
            Exception(
                "Please retry in 2s."
            ),
            300,
        ),
        (
            "No retry information",
            Exception(
                "Temporary provider failure."
            ),
            300,
        ),
    ]

    for name, error, expected_minimum in test_cases:

        actual = extract_retry_seconds(
            error,
            default=expected_minimum,
        )

        print()
        print(name)
        print(
            f"  Parsed delay : {actual} seconds"
        )
        print(
            f"  Minimum      : {expected_minimum} seconds"
        )

        assert actual >= expected_minimum, (
            f"{name}: expected at least "
            f"{expected_minimum}, got {actual}"
        )

    print()
    print("=" * 70)
    print("ALL PROVIDER DELAY TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()