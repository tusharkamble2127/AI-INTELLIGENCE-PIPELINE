from __future__ import annotations

from typing import List

import tiktoken


class TextChunker:
    """
    Token-aware text chunker.

    Keeps chunks below a configurable token budget
    to reduce the chance of 413/context-limit errors.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        overlap_tokens: int = 200,
    ) -> None:

        if overlap_tokens >= max_tokens:
            raise ValueError(
                "overlap_tokens must be smaller "
                "than max_tokens"
            )

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

        self.encoder = (
            tiktoken.get_encoding(
                "cl100k_base"
            )
        )

    def count_tokens(
        self,
        text: str,
    ) -> int:
        return len(
            self.encoder.encode(
                text
            )
        )

    def split(
        self,
        text: str,
    ) -> List[str]:

        tokens = self.encoder.encode(
            text
        )

        if len(tokens) <= self.max_tokens:
            return [text]

        chunks: List[str] = []

        start = 0

        while start < len(tokens):

            end = min(
                start + self.max_tokens,
                len(tokens),
            )

            chunk_tokens = tokens[
                start:end
            ]

            chunk_text = (
                self.encoder.decode(
                    chunk_tokens
                )
            )

            chunks.append(
                chunk_text
            )

            if end >= len(tokens):
                break

            start = (
                end
                - self.overlap_tokens
            )

        return chunks