from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.crawlers.news_crawler import (
    NEWS_SOURCES,
    crawl_news,
)
from src.processors.news_validator import (
    validate_news_record,
)


OUTPUT_DIR = Path("data")

NEWS_FILE = (
    OUTPUT_DIR / "news.json"
)

NEWS_REJECTIONS_FILE = (
    OUTPUT_DIR / "news_rejections.json"
)


def write_json(
    path: Path,
    data: Any,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def build_record(
    article: dict[str, Any],
) -> dict[str, Any]:

    return {
        "schemaVersion": "1.0",
        "recordType": "NEWS",
        "source": {
            "name": article[
                "source"
            ],
            "url": article.get(
                "finalUrl",
                article["url"],
            ),
        },
        "content": {
            "title": article.get(
                "title",
                "",
            ),
            "url": article["url"],
            "publishedAt": article[
                "publishedAt"
            ],
            "summary": article.get(
                "summary",
                "",
            ),
            "content": article.get(
                "content",
                "",
            ),
        },
        "collectedAt": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }


async def main() -> None:

    print("=" * 70)
    print("AI NEWS PIPELINE")
    print("=" * 70)

    print(
        "Sources configured: "
        f"{len(NEWS_SOURCES)}"
    )

    for source in NEWS_SOURCES:
        print(
            f" - {source}"
        )

    print()
    print(
        "Collecting articles from "
        "the last 24 hours..."
    )

    articles = await crawl_news(
        hours=24
    )

    records: list[
        dict[str, Any]
    ] = []

    rejections: list[
        dict[str, Any]
    ] = []

    for article in articles:

        record = build_record(
            article
        )

        errors = (
            validate_news_record(
                record
            )
        )

        if errors:

            rejections.append(
                {
                    "url": article.get(
                        "url"
                    ),
                    "source": article.get(
                        "source"
                    ),
                    "errors": errors,
                }
            )

            continue

        records.append(
            record
        )

    # Final URL deduplication.
    unique: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:

        url = record[
            "content"
        ]["url"]

        unique[url] = record

    records = list(
        unique.values()
    )

    write_json(
        NEWS_FILE,
        records,
    )

    write_json(
        NEWS_REJECTIONS_FILE,
        rejections,
    )

    print()
    print("=" * 70)
    print("NEWS PIPELINE RESULT")
    print("=" * 70)

    print(
        f"Articles collected : "
        f"{len(articles)}"
    )

    print(
        f"Valid news records  : "
        f"{len(records)}"
    )

    print(
        f"Rejected            : "
        f"{len(rejections)}"
    )

    print(
        f"Freshness window    : "
        f"24 hours"
    )

    print(
        f"Output              : "
        f"{NEWS_FILE}"
    )

    print(
        f"Rejections          : "
        f"{NEWS_REJECTIONS_FILE}"
    )


if __name__ == "__main__":
    asyncio.run(main())