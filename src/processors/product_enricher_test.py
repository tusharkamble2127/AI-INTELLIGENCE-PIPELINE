from __future__ import annotations

import asyncio
import json
import os

import aiohttp
from dotenv import load_dotenv

from src.crawlers.producthunt_test import (
    fetch_products,
)
from src.processors.product_enricher import (
    ProductEnricher,
)


async def main() -> None:
    load_dotenv()

    token = os.getenv(
        "PRODUCT_HUNT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "PRODUCT_HUNT_TOKEN is missing from .env"
        )

    async with aiohttp.ClientSession() as session:

        # --------------------------------------------
        # 1. Fetch products from Product Hunt
        # --------------------------------------------

        data = await fetch_products(
            session=session,
            token=token,
        )

        if "errors" in data:
            raise RuntimeError(
                f"Product Hunt GraphQL error: "
                f"{data['errors']}"
            )

        posts = (
            data
            .get("data", {})
            .get("posts", {})
            .get("edges", [])
        )

        if not posts:
            raise RuntimeError(
                "No Product Hunt products returned."
            )

        # --------------------------------------------
        # 2. Select first product
        # --------------------------------------------

        product = posts[0].get(
            "node",
            {},
        )

        print("=" * 70)
        print("PRODUCT ENRICHER INTEGRATION TEST")
        print("=" * 70)

        print(
            f"Product Hunt product: "
            f"{product.get('name')}"
        )

        print(
            f"Website: "
            f"{product.get('website')}"
        )

        print()

        # --------------------------------------------
        # 3. Run ProductEnricher
        # --------------------------------------------

        enricher = ProductEnricher(
            session=session
        )

        result = await enricher.enrich(
            product
        )

    print("=" * 70)
    print("ENRICHMENT RESULT")
    print("=" * 70)

    if result is None:
        print(
            "RESULT: Product could not be "
            "enriched into a final valid record."
        )
        return

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())