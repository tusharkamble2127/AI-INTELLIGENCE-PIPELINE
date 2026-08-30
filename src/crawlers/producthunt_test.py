from __future__ import annotations

import asyncio
import os
from typing import Any

import aiohttp
from dotenv import load_dotenv


PRODUCT_HUNT_API = (
    "https://api.producthunt.com/v2/api/graphql"
)


QUERY = """
query {
    posts(first: 10) {
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


async def fetch_products(
    session: aiohttp.ClientSession,
    token: str,
) -> dict[str, Any]:

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "query": QUERY,
    }

    async with session.post(
        PRODUCT_HUNT_API,
        headers=headers,
        json=payload,
        timeout=aiohttp.ClientTimeout(
            total=30
        ),
    ) as response:

        response.raise_for_status()

        return await response.json()


async def main() -> None:

    load_dotenv()

    token = os.getenv(
        "PRODUCT_HUNT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "PRODUCT_HUNT_TOKEN is missing "
            "from .env"
        )

    async with aiohttp.ClientSession() as session:

        data = await fetch_products(
            session=session,
            token=token,
        )

    print("=" * 70)
    print("PRODUCT HUNT API TEST")
    print("=" * 70)

    if "errors" in data:

        print("GraphQL returned errors:")
        print(data["errors"])
        return

    posts = (
        data
        .get("data", {})
        .get("posts", {})
        .get("edges", [])
    )

    print(
        f"Products received: {len(posts)}"
    )

    for index, edge in enumerate(
        posts,
        start=1,
    ):

        product = edge.get(
            "node",
            {},
        )

        print()
        print(f"Product {index}")
        print(
            f"Name    : "
            f"{product.get('name')}"
        )
        print(
            f"Website : "
            f"{product.get('website')}"
        )

        topics = [
            item.get(
                "node",
                {}
            ).get("name")
            for item in (
                product
                .get("topics", {})
                .get("edges", [])
            )
        ]

        print(
            f"Topics  : "
            f"{', '.join(topics)}"
        )


if __name__ == "__main__":
    asyncio.run(main())