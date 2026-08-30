from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import aiohttp

from src.crawlers.yc_startup_test import (
    fetch_yc_companies,
)
from src.processors.startup_filter import (
    calculate_ai_score,
    is_ai_startup,
)
from src.utils.data_writer import (
    write_json_records,
)


TARGET_STARTUPS = 1000


def normalize_company_name(
    name: str,
) -> str:
    return " ".join(
        name.strip().split()
    )


def startup_to_output(
    company: dict[str, Any],
) -> dict[str, Any]:

    return {
        "schemaVersion": "1.0",
        "recordType": "STARTUP",
        "source": {
            "name": "Y Combinator",
            "url": company["url"],
        },
        "content": {
            "entityName": normalize_company_name(
                company["name"]
            ),
            "data": {
                "employeeCount": company.get(
                    "team_size"
                ),
            },
        },
        "collectedAt": datetime.now(
            timezone.utc
        ).isoformat(),
    }


async def main() -> None:

    async with aiohttp.ClientSession() as session:

        companies = await fetch_yc_companies(
            session
        )

    candidates = []

    for company in companies:

        if not is_ai_startup(company):
            continue

        score, signals = calculate_ai_score(
            company
        )

        candidates.append(
            {
                "company": company,
                "score": score,
                "signals": signals,
            }
        )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["company"]["name"].lower(),
        )
    )

    unique_companies = []
    seen_urls = set()
    seen_names = set()

    for candidate in candidates:

        company = candidate["company"]

        source_url = company.get("url")

        raw_name = normalize_company_name(
            company.get("name", "")
        )

        normalized_name = raw_name.lower()

        if not source_url:
            continue

        if source_url in seen_urls:
            continue

        if normalized_name in seen_names:
            continue

        seen_urls.add(source_url)
        seen_names.add(normalized_name)

        unique_companies.append(
            company
        )

        if len(unique_companies) >= TARGET_STARTUPS:
            break

    records = [
        startup_to_output(company)
        for company in unique_companies
    ]

    write_json_records(
        filename="startups.json",
        records=records,
    )

    print("=" * 70)
    print("STARTUP DATASET")
    print("=" * 70)

    print(
        f"YC companies     : {len(companies)}"
    )

    print(
        f"AI candidates    : {len(candidates)}"
    )

    print(
        f"Final startups   : {len(records)}"
    )

    print(
        "Output           : "
        "data/startups.json"
    )


if __name__ == "__main__":
    asyncio.run(main())