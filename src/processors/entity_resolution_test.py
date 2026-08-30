from __future__ import annotations

from src.processors.entity_resolver import (
    resolve_many,
)


TEST_NAMES = [
    "OpenAI",
    "Open AI",
    "OpenAI, Inc.",
    "Anthropic, Inc.",
    "Google DeepMind",
    "NVIDIA Corporation",
    "HuggingFace",
    "Hugging Face",
    "Mistral AI",
    "Mistral AI, Inc.",
    "Unknown Startup XYZ",
]


def main() -> None:

    print("=" * 70)
    print("ENTITY RESOLUTION TEST")
    print("=" * 70)

    results = resolve_many(
        TEST_NAMES
    )

    for result in results:

        print(
            f"{result['rawName']}"
            " -> "
            f"{result['canonicalName']}"
            " | "
            f"{result['method']}"
            " | "
            f"confidence="
            f"{result['confidence']}"
        )


if __name__ == "__main__":
    main()