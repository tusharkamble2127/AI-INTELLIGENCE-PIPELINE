from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv

from src.crawlers.product_site_crawler import (
    ProductSiteCrawler,
)
from src.llm.groq_provider import GroqProvider
from src.llm.prompts import (
    PRODUCT_EXTRACTION_PROMPT,
)
import aiohttp


async def main() -> None:
    load_dotenv()

    test_url = (
        "https://enter.converge.ai/?ref=producthunt"
    )

    async with aiohttp.ClientSession() as session:

        crawler = ProductSiteCrawler(
            session
        )

        result = await crawler.fetch(
            test_url
        )

    text = result["text"]

    prompt = PRODUCT_EXTRACTION_PROMPT.format(
        text=text
    )

    provider = GroqProvider()

    raw_response = await provider.generate(
        prompt,
        max_tokens=500,
    )

    print("=" * 70)
    print("PRODUCT EXTRACTION TEST")
    print("=" * 70)

    print("RAW LLM RESPONSE:")
    print(raw_response)

    print()

    try:
        parsed = json.loads(
            raw_response
        )

        print("PARSED JSON:")
        print(
            json.dumps(
                parsed,
                indent=2,
                ensure_ascii=False,
            )
        )

    except json.JSONDecodeError as exc:

        print(
            "ERROR: LLM did not return valid JSON"
        )

        print(exc)


if __name__ == "__main__":
    asyncio.run(main())