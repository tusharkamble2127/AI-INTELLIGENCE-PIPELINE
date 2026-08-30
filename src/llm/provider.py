from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Common interface for all LLM providers.
    """

    name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate text from the provider.
        """
        raise NotImplementedError

    async def health_check(self) -> bool:
        """
        Basic provider availability check.
        """
        try:
            result = await self.generate(
                "Reply with exactly: OK",
                max_tokens=10,
            )

            return result.strip() == "OK"

        except Exception:
            return False