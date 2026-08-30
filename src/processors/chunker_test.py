from __future__ import annotations

from src.processors.chunker import (
    TextChunker,
)


def main() -> None:

    chunker = TextChunker(
        max_tokens=100,
        overlap_tokens=20,
    )

    text = (
        "Artificial intelligence is transforming "
        "software development. " * 300
    )

    chunks = chunker.split(
        text
    )

    print("=" * 70)
    print("CHUNKER TEST")
    print("=" * 70)

    print(
        f"Original tokens : "
        f"{chunker.count_tokens(text)}"
    )

    print(
        f"Chunks          : "
        f"{len(chunks)}"
    )

    for index, chunk in enumerate(
        chunks[:3],
        start=1,
    ):

        print(
            f"Chunk {index}: "
            f"{chunker.count_tokens(chunk)} tokens"
        )


if __name__ == "__main__":
    main()