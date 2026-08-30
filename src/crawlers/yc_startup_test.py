from __future__ import annotations

import asyncio
import aiohttp


YC_API_URL = (
    "https://yc-oss.github.io/api/companies/all.json"
)


async def fetch_yc_companies(
    session: aiohttp.ClientSession,
) -> list[dict]:
    """
    Fetch all publicly launched YC companies
    from the YC OSS API.
    """

    async with session.get(
        YC_API_URL,
        timeout=aiohttp.ClientTimeout(total=60),
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Intelligence-Pipeline/1.0",
        },
    ) as response:

        response.raise_for_status()

        return await response.json()


async def main() -> None:

    async with aiohttp.ClientSession() as session:

        companies = await fetch_yc_companies(
            session
        )

    print("=" * 70)
    print("YC STARTUP API TEST")
    print("=" * 70)

    print(
        f"Companies received: {len(companies)}"
    )

    print()

    for index, company in enumerate(
        companies[:5],
        start=1,
    ):

        print(f"Company {index}")
        print(company)
        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())