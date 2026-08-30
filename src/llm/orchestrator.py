from __future__ import annotations

import logging

from src.llm.deepseek_provider import (
    DeepSeekProvider,
)
from src.llm.errors import (
    is_quota_exhausted,
)
from src.llm.gemini_provider import (
    GeminiProvider,
)
from src.llm.groq_provider import (
    GroqProvider,
)
from src.llm.provider import (
    LLMProvider,
)
from src.llm.provider_state import (
    ProviderStateManager,
    extract_retry_seconds,
)
from src.llm.retry import (
    llm_retry,
)


logger = logging.getLogger(
    "llm_orchestrator"
)


class LLMOrchestrator:
    """
    Multi-provider LLM fallback system.

    Provider priority:

        Gemini -> Groq -> DeepSeek

    Provider state is tracked so that a provider
    that is temporarily unavailable or exhausted
    is skipped during its cooldown period.
    """

    def __init__(self) -> None:

        self.providers: list[
            LLMProvider
        ] = [
            GeminiProvider(),
            GroqProvider(),
            DeepSeekProvider(),
        ]

        self.state = (
            ProviderStateManager()
        )

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1000,
    ) -> str:

        errors: list[str] = []

        for provider in self.providers:

            # -------------------------------------------------
            # Skip temporarily disabled providers
            # -------------------------------------------------

            if not self.state.is_available(
                provider.name
            ):

                provider_state = (
                    self.state.get(
                        provider.name
                    )
                )

                logger.info(
                    "Skipping provider %s "
                    "(temporarily disabled: %s)",
                    provider.name,
                    provider_state.reason,
                )

                errors.append(
                    f"{provider.name}: "
                    "temporarily disabled"
                )

                continue

            logger.info(
                "Trying LLM provider: %s",
                provider.name,
            )

            try:

                result = await llm_retry(
                    lambda: provider.generate(
                        prompt,
                        max_tokens=max_tokens,
                    ),
                    max_retries=3,
                )

                if not result.strip():
                    raise RuntimeError(
                        f"{provider.name} "
                        "returned empty output"
                    )

                logger.info(
                    "Provider succeeded: %s",
                    provider.name,
                )

                return result.strip()

            except Exception as exc:

                logger.warning(
                    "Provider failed: %s - %s",
                    provider.name,
                    exc,
                )

                errors.append(
                    f"{provider.name}: {exc}"
                )

                # -------------------------------------------------
                # Quota/balance exhaustion
                # -------------------------------------------------

                if is_quota_exhausted(
                    exc
                ):

                    cooldown_seconds = (
                        extract_retry_seconds(
                            exc,
                            default=300,
                        )
                    )

                    self.state.disable(
                        provider.name,
                        seconds=cooldown_seconds,
                        reason=str(exc),
                    )

                    logger.warning(
                        "Provider %s disabled "
                        "for %s seconds",
                        provider.name,
                        cooldown_seconds,
                    )

                # Move immediately to the next provider.
                continue

        raise RuntimeError(
            "All LLM providers failed or "
            "are temporarily unavailable:\n"
            + "\n".join(errors)
        )