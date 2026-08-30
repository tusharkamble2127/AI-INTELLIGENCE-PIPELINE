from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.llm.errors import is_retryable_error


T = TypeVar("T")


async def llm_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
) -> T:
    """
    Retry transient LLM/provider failures using
    exponential backoff with jitter.

    Permanent failures and exhausted quotas are
    immediately propagated to the orchestrator.
    """

    for attempt in range(
        max_retries + 1
    ):

        try:
            return await operation()

        except Exception as exc:

            if (
                not is_retryable_error(exc)
                or attempt >= max_retries
            ):
                raise

            exponential_delay = min(
                max_delay,
                base_delay * (2 ** attempt),
            )

            jitter = random.uniform(
                0,
                exponential_delay * 0.25,
            )

            delay = (
                exponential_delay
                + jitter
            )

            print(
                f"LLM retryable error: {exc}"
            )

            print(
                f"Retrying in {delay:.2f}s "
                f"(attempt "
                f"{attempt + 1}/{max_retries})"
            )

            await asyncio.sleep(
                delay
            )

    raise RuntimeError(
        "Unexpected retry state"
    )