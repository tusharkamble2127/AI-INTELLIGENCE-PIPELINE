from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.llm.provider import LLMProvider


load_dotenv()


class DeepSeekProvider(LLMProvider):
    """
    DeepSeek provider using NVIDIA NIM's
    OpenAI-compatible hosted API.

    NVIDIA model:
        deepseek-ai/deepseek-v4-flash-0731

    Endpoint:
        https://integrate.api.nvidia.com/v1
    """

    name = "deepseek"

    MODEL = "deepseek-ai/deepseek-v4-pro-0813"

    BASE_URL = (
        "https://integrate.api.nvidia.com/v1"
    )

    def __init__(self) -> None:
        api_key = os.getenv(
            "NVIDIA_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is missing from .env"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
        )

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate text using DeepSeek V4 Flash
        through NVIDIA NIM.
        """

        response = await self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            stream=False,
        )

        if not response.choices:
            raise RuntimeError(
                "NVIDIA DeepSeek returned no choices"
            )

        message = response.choices[0].message

        content = message.content

        if content:
            content = content.strip()

            if content:
                return content

        # Some reasoning-capable models may expose
        # reasoning separately. Use it as a fallback
        # only when final content is unavailable.
        reasoning = getattr(
            message,
            "reasoning",
            None,
        )

        if reasoning:
            reasoning = reasoning.strip()

            if reasoning:
                return reasoning

        raise RuntimeError(
            "NVIDIA DeepSeek returned empty final content"
        )