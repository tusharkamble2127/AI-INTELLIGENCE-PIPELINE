from __future__ import annotations

import asyncio

import aiohttp

from src.crawlers.product_site_crawler import (
    ProductSiteCrawler,
)
from src.processors.pricing_detector import (
    find_pricing_links,
)


async def main() -> None:

    product_url = (
        "https://enter.converge.ai/?ref=producthunt"
    )

    async with aiohttp.ClientSession() as session:

        crawler = ProductSiteCrawler(
            session
        )

        # First crawl the main product page.
        product_result = await crawler.fetch(
            product_url
        )

        pricing_links = find_pricing_links(
            html=product_result["html"],
            base_url=str(product_result["url"]),
        )

        print("=" * 70)
        print("PRICING PAGE TEST")
        print("=" * 70)

        print(
            f"Pricing links found: "
            f"{len(pricing_links)}"
        )

        if not pricing_links:
            print(
                "No pricing page discovered."
            )
            return

        pricing_url = pricing_links[0]

        print(
            f"Pricing URL: {pricing_url}"
        )

        # Crawl the pricing page using the same
        # aiohttp -> Playwright fallback.
        pricing_result = await crawler.fetch(
            pricing_url
        )

        print()
        print(
            f"Fetch method: "
            f"{pricing_result['method']}"
        )

        print(
            f"Final URL: "
            f"{pricing_result['url']}"
        )

        print(
            f"HTML chars: "
            f"{len(pricing_result['html']):,}"
        )

        print(
            f"Text chars: "
            f"{len(pricing_result['text']):,}"
        )

        print()
        print("PRICING PAGE TEXT")
        print("-" * 70)
        print(
            pricing_result["text"][:5000]
        )


if __name__ == "__main__":
    asyncio.run(main())