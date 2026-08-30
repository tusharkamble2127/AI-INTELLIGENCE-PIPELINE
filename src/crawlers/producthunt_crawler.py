from __future__ import annotations

import asyncio
import random
from typing import Any

import aiohttp


PRODUCT_HUNT_API = (
    "https://api.producthunt.com/v2/api/graphql"
)


PRODUCT_QUERY = """
query GetProducts($first: Int!, $after: String) {

    posts(first: $first, after: $after) {

        pageInfo {
            hasNextPage
            endCursor
        }

        edges {

            node {

                id
                name
                tagline
                url
                website
                createdAt

                topics {

                    edges {

                        node {
                            name
                        }
                    }
                }

                makers {

                    id
                    name
                }
            }
        }
    }
}
"""


class ProductHuntCrawler:
    """
    Production Product Hunt GraphQL crawler.

    Features:
    - Cursor-based pagination
    - 429 rate-limit handling
    - Retry-After support
    - Exponential backoff
    - Random jitter
    - Small delay between pages
    - GraphQL error handling
    """

    MAX_RETRIES = 4

    BASE_BACKOFF_SECONDS = 3.0

    MAX_BACKOFF_SECONDS = 30.0

    PAGE_DELAY_MIN = 1.0

    PAGE_DELAY_MAX = 2.0

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
    ) -> None:

        self.session = session
        self.token = token
        self.rate_limited = False

    @staticmethod
    def _parse_retry_after(
        response: aiohttp.ClientResponse,
    ) -> float | None:
        """
        Read Retry-After header when the API provides it.
        """

        value = response.headers.get(
            "Retry-After"
        )

        if not value:
            return None

        try:
            return max(
                0.0,
                float(value),
            )
        except ValueError:
            return None

    @classmethod
    def _calculate_backoff(
        cls,
        attempt: int,
    ) -> float:
        """
        Exponential backoff with jitter.

        Attempt 0 -> ~2 sec
        Attempt 1 -> ~4 sec
        Attempt 2 -> ~8 sec
        ...
        """

        exponential = min(
            cls.MAX_BACKOFF_SECONDS,
            cls.BASE_BACKOFF_SECONDS
            * (2 ** attempt),
        )

        jitter = random.uniform(
            0.2,
            1.0,
        )

        return exponential + jitter

    async def fetch_page(
        self,
        *,
        first: int = 10,
        after: str | None = None,
    ) -> dict[str, Any]:

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.token}"
            ),
            "User-Agent": (
                "AI-Intelligence-Pipeline/1.0"
            ),
        }

        variables = {
            "first": first,
            "after": after,
        }

        payload = {
            "query": PRODUCT_QUERY,
            "variables": variables,
        }

        for attempt in range(
            self.MAX_RETRIES
        ):

            try:

                async with self.session.post(
                    PRODUCT_HUNT_API,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(
                        total=30
                    ),
                ) as response:

                    # -----------------------------------------
                    # Handle Product Hunt rate limiting
                    # -----------------------------------------

                    if response.status == 429:

                        retry_after = (
                            self._parse_retry_after(
                                response
                            )
                        )

                        if retry_after is None:

                            retry_after = (
                                self._calculate_backoff(
                                    attempt
                                )
                            )
                        else:
                            # Add a tiny random jitter even
                            # when Retry-After is provided.
                            retry_after += (
                                random.uniform(
                                    0.2,
                                    1.0,
                                )
                            )

                        print(
                            "Product Hunt API "
                            f"rate limited (429). "
                            f"Retrying in "
                            f"{retry_after:.2f}s "
                            f"(attempt "
                            f"{attempt + 1}/"
                            f"{self.MAX_RETRIES})"
                        )

                        await asyncio.sleep(
                            retry_after
                        )

                        continue

                    # -----------------------------------------
                    # Other HTTP errors
                    # -----------------------------------------

                    response.raise_for_status()

                    data = await response.json()

                    # -----------------------------------------
                    # GraphQL errors
                    # -----------------------------------------

                    if "errors" in data:

                        raise RuntimeError(
                            "Product Hunt "
                            "GraphQL error: "
                            f"{data['errors']}"
                        )

                    return data

            except aiohttp.ClientResponseError as exc:

                # A 429 may also surface here depending
                # on aiohttp behavior.
                if exc.status == 429:

                    delay = (
                        self._calculate_backoff(
                            attempt
                        )
                    )

                    print(
                        "Product Hunt API "
                        f"rate limited (429). "
                        f"Retrying in "
                        f"{delay:.2f}s "
                        f"(attempt "
                        f"{attempt + 1}/"
                        f"{self.MAX_RETRIES})"
                    )

                    await asyncio.sleep(
                        delay
                    )

                    continue

                raise

            except (
                aiohttp.ClientConnectionError,
                asyncio.TimeoutError,
            ) as exc:

                # Temporary network errors are also retried.
                if (
                    attempt
                    >= self.MAX_RETRIES - 1
                ):
                    raise

                delay = (
                    self._calculate_backoff(
                        attempt
                    )
                )

                print(
                    "Product Hunt temporary "
                    f"network error: {exc}"
                )

                print(
                    f"Retrying in "
                    f"{delay:.2f}s "
                    f"(attempt "
                    f"{attempt + 1}/"
                    f"{self.MAX_RETRIES})"
                )

                await asyncio.sleep(
                    delay
                )

        self.rate_limited = True
        print(
            "WARNING: Product Hunt API remained rate-limited after "
            f"{self.MAX_RETRIES} attempts. Stopping Product Hunt collection "
            "gracefully instead of crashing the whole pipeline."
        )
        return {
            "data": {
                "posts": {
                    "edges": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

    async def iter_products(
        self,
        *,
        page_size: int = 10,
        max_products: int | None = None,
    ):
        """
        Yield Product Hunt products page by page.

        A short delay is inserted between successful
        pages to reduce API pressure.
        """

        after: str | None = None

        yielded = 0

        while True:

            data = await self.fetch_page(
                first=min(page_size, 10),
                after=after,
            )

            if self.rate_limited:
                return

            posts = (
                data
                .get("data", {})
                .get("posts", {})
            )

            edges = posts.get(
                "edges",
                [],
            )

            if not edges:
                break

            for edge in edges:

                product = edge.get(
                    "node",
                    {},
                )

                if not product:
                    continue

                yield product

                yielded += 1

                if (
                    max_products is not None
                    and yielded
                    >= max_products
                ):
                    return

            page_info = posts.get(
                "pageInfo",
                {},
            )

            if not page_info.get(
                "hasNextPage",
                False,
            ):
                break

            after = page_info.get(
                "endCursor"
            )

            if not after:
                break

            # ---------------------------------------------
            # Gentle page-to-page throttling
            # ---------------------------------------------

            await asyncio.sleep(
                random.uniform(
                    self.PAGE_DELAY_MIN,
                    self.PAGE_DELAY_MAX,
                )
            )