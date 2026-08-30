from __future__ import annotations

import asyncio
import json

import aiohttp
from dotenv import load_dotenv

from src.crawlers.product_site_crawler import (
    ProductSiteCrawler,
)
from src.processors.pricing_detector import (
    find_pricing_links,
)
from src.llm.groq_provider import GroqProvider
from src.llm.prompts import (
    PRICING_EXTRACTION_PROMPT,
)
from src.models.pricing_extraction import (
    PricingExtraction,
)


async def main() -> None:
    load_dotenv()

    product_url = (
        "https://enter.converge.ai/?ref=producthunt"
    )

    async with aiohttp.ClientSession() as session:

        crawler = ProductSiteCrawler(
            session
        )

        product_result = await crawler.fetch(
            product_url
        )

        pricing_links = find_pricing_links(
            html=product_result["html"],
            base_url=str(product_result["url"]),
        )

        if not pricing_links:
            raise RuntimeError(
                "No pricing page found"
            )

        pricing_result = await crawler.fetch(
            pricing_links[0]
        )

    pricing_text = pricing_result["text"]

    prompt = PRICING_EXTRACTION_PROMPT.format(
        text=pricing_text
    )

    provider = GroqProvider()

    raw_response = await provider.generate(
        prompt,
        max_tokens=300,
    )

    print("=" * 70)
    print("PRICING EXTRACTION TEST")
    print("=" * 70)

    print("RAW LLM RESPONSE:")
    print(raw_response)

    parsed = json.loads(
        raw_response
    )

    extraction = PricingExtraction.model_validate(
        parsed
    )

    print()
    print("VALIDATED EXTRACTION:")
    print(
        extraction.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    asyncio.run(main())