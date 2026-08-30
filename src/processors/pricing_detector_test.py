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

    url = (
        "https://enter.converge.ai/?ref=producthunt"
    )

    async with aiohttp.ClientSession() as session:

        crawler = ProductSiteCrawler(
            session
        )

        result = await crawler.fetch(
            url
        )

    pricing_links = find_pricing_links(
        html=result["html"],
        base_url=str(result["url"]),
    )

    print("=" * 70)
    print("PRICING LINK DETECTOR TEST")
    print("=" * 70)

    print(
        f"Pricing links found: "
        f"{len(pricing_links)}"
    )

    for link in pricing_links:
        print(link)


if __name__ == "__main__":
    asyncio.run(main())