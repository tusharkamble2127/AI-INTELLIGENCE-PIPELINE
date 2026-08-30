from __future__ import annotations

from src.llm.provider_state import (
    ProviderStateManager,
)


def main() -> None:
    manager = ProviderStateManager()

    print("=" * 70)
    print("PROVIDER STATE TEST")
    print("=" * 70)

    print(
        "Gemini initially available:",
        manager.is_available("gemini"),
    )

    manager.disable(
        "gemini",
        seconds=60,
        reason="quota exhausted",
    )

    print(
        "Gemini after disable:",
        manager.is_available("gemini"),
    )

    print(
        "Gemini reason:",
        manager.get("gemini").reason,
    )

    print(
        "Groq available:",
        manager.is_available("groq"),
    )


if __name__ == "__main__":
    main()