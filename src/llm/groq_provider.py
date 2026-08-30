from __future__ import annotations

import os

from groq import AsyncGroq

from src.llm.provider import LLMProvider


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing from .env"
            )

        self.client = AsyncGroq(
            api_key=api_key
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        )

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
    ) -> str:
        """
        Generate a response using Groq GPT-OSS.

        A larger completion budget is important because
        GPT-OSS may consume part of the budget for reasoning.
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_completion_tokens=max_tokens,
            reasoning_effort="low",
            include_reasoning=False,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "Groq returned empty final content"
            )

        return content.strip()