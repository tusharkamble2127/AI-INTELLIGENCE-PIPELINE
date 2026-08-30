from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import aiohttp


T = TypeVar("T")


RETRYABLE_STATUS_CODES = {
    408, 429, 500, 502, 503, 504
}


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    """
    Execute an async operation with exponential backoff and jitter.

    Retryable HTTP failures:
        408, 429, 500, 502, 503, 504
    """

    for attempt in range(max_retries + 1):

        try:
            return await operation()

        except aiohttp.ClientResponseError as exc:

            if (
                exc.status not in RETRYABLE_STATUS_CODES
                or attempt == max_retries
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

            delay = exponential_delay + jitter

            print(
                f"Retryable HTTP error {exc.status}. "
                f"Retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )

            await asyncio.sleep(delay)

        except (
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
        ):

            if attempt == max_retries:
                raise

            exponential_delay = min(
                max_delay,
                base_delay * (2 ** attempt),
            )

            jitter = random.uniform(
                0,
                exponential_delay * 0.25,
            )

            delay = exponential_delay + jitter

            print(
                f"Network error. "
                f"Retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )

            await asyncio.sleep(delay)

    raise RuntimeError("Unexpected retry state")