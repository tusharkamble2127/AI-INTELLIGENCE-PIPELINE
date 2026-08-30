from __future__ import annotations

import asyncio

import aiohttp

from src.crawlers.yc_startup_test import (
    fetch_yc_companies,
)
from src.processors.startup_filter import (
    calculate_ai_score,
    is_ai_startup,
)


async def main() -> None:

    async with aiohttp.ClientSession() as session:

        companies = await fetch_yc_companies(
            session
        )

    ai_companies = []

    for company in companies:

        if is_ai_startup(company):

            score, signals = calculate_ai_score(
                company
            )

            ai_companies.append(
                (
                    company,
                    score,
                    signals,
                )
            )

    ai_companies.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    print("=" * 70)
    print("YC AI STARTUP FILTER TEST")
    print("=" * 70)

    print(
        f"Total YC companies : {len(companies)}"
    )

    print(
        f"AI candidates      : {len(ai_companies)}"
    )

    print()

    for index, (
        company,
        score,
        signals,
    ) in enumerate(
        ai_companies[:20],
        start=1,
    ):

        print(f"{index}. {company['name']}")
        print(f"   Score   : {score}")
        print(f"   Signals : {', '.join(signals)}")
        print(f"   Website : {company.get('website')}")
        print(f"   YC URL  : {company.get('url')}")
        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())