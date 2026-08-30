from __future__ import annotations

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

from src.crawlers.producthunt_crawler import ProductHuntCrawler


TARGET = "Echovault Digital Legacy"


async def main() -> None:
    load_dotenv()

    token = os.getenv("PRODUCT_HUNT_TOKEN")

    if not token:
        raise RuntimeError(
            "PRODUCT_HUNT_TOKEN is missing from .env"
        )

    async with aiohttp.ClientSession() as session:

        crawler = ProductHuntCrawler(
            session=session,
            token=token,
        )

        scanned = 0

        print("=" * 70)
        print("PRODUCT HUNT TARGET SEARCH")
        print("=" * 70)

        async for product in crawler.iter_products(
            page_size=10,
            max_products=500,
        ):
            scanned += 1

            name = product.get("name", "")

            if name.strip().lower() == TARGET.lower():
                print()
                print("TARGET FOUND")
                print("-" * 70)
                print(f"Name    : {product.get('name')}")
                print(f"Website : {product.get('website')}")
                print(f"URL     : {product.get('url')}")
                print(f"ID      : {product.get('id')}")
                print(f"Scanned : {scanned}")
                print("-" * 70)
                return

        print()
        print("TARGET NOT FOUND")
        print(f"Scanned: {scanned}")


if __name__ == "__main__":
    asyncio.run(main())