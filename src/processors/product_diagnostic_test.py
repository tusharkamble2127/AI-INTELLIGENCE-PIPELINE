from __future__ import annotations

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

from src.crawlers.producthunt_crawler import ProductHuntCrawler
from src.processors.product_diagnostic import (
    diagnose_product_enrichment,
)
from src.processors.product_enricher import ProductEnricher


TARGET_PRODUCTS = {
    "PageIndex",
}


async def main() -> None:
    load_dotenv()

    token = os.getenv(
        "PRODUCT_HUNT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "PRODUCT_HUNT_TOKEN is missing from .env"
        )

    found: set[str] = set()

    async with aiohttp.ClientSession() as session:

        crawler = ProductHuntCrawler(
            session=session,
            token=token,
        )

        enricher = ProductEnricher(
            session=session
        )

        print("=" * 70)
        print("PRODUCT DIAGNOSTIC TEST")
        print("=" * 70)

        async for product in crawler.iter_products(
            page_size=10,
            max_products=100,
        ):

            name = product.get(
                "name"
            )

            if name not in TARGET_PRODUCTS:
                continue

            # Prevent duplicate diagnostics.
            if name in found:
                continue

            found.add(name)

            print()
            print(
                f"Product: {name}"
            )

            result = (
                await diagnose_product_enrichment(
                    enricher=enricher,
                    product=product,
                )
            )

            print(
                f"Reason: "
                f"{result.get('reason')}"
            )

            if result.get("error"):
                print(
                    f"Error: "
                    f"{result['error']}"
                )

            if result.get("startup_name"):
                print(
                    f"Startup: "
                    f"{result['startup_name']}"
                )

            if result.get("pricing_model"):
                print(
                    f"Pricing: "
                    f"{result['pricing_model']}"
                )

            print("-" * 70)

            if found == TARGET_PRODUCTS:
                break

    print()
    print("=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)

    print(
        f"Found targets: "
        f"{len(found)}/{len(TARGET_PRODUCTS)}"
    )

    missing = TARGET_PRODUCTS - found

    if missing:
        print(
            "Not found in scanned pages:"
        )
        for name in sorted(missing):
            print(
                f" - {name}"
            )


if __name__ == "__main__":
    asyncio.run(main())