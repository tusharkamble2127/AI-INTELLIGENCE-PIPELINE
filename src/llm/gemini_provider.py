from __future__ import annotations

import os

from google import genai

from src.llm.provider import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from .env"
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = "gemini-3.7-flash"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1000,
    ) -> str:

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        # Normal text output
        if getattr(response, "text", None):
            return response.text.strip()

        # Defensive fallback for cases where .text is empty
        candidates = getattr(response, "candidates", None) or []

        for candidate in candidates:
            content = getattr(candidate, "content", None)

            if not content:
                continue

            parts = getattr(content, "parts", None) or []

            for part in parts:
                text = getattr(part, "text", None)

                if text:
                    return text.strip()

        raise RuntimeError(
            "Gemini returned no text content"
        )