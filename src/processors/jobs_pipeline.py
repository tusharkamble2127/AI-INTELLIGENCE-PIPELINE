from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.crawlers.jobs_crawler import (
    JOB_SOURCES,
    crawl_jobs,
)
from src.processors.jobs_validator import (
    validate_job_record,
)


OUTPUT_DIR = Path("data")

JOBS_FILE = (
    OUTPUT_DIR / "jobs.json"
)

JOBS_REJECTIONS_FILE = (
    OUTPUT_DIR / "job_rejections.json"
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


def infer_role_family(
    title: str,
) -> str:

    text = title.lower()

    if any(
        key in text
        for key in (
            "machine learning",
            "ml engineer",
            "ai engineer",
            "artificial intelligence",
            "deep learning",
            "data scientist",
            "data science",
            "applied scientist",
        )
    ):
        return "AI / ML"

    if any(
        key in text
        for key in (
            "software engineer",
            "software developer",
            "backend",
            "frontend",
            "full stack",
            "developer",
            "programmer",
        )
    ):
        return "Engineering"

    if any(
        key in text
        for key in (
            "devops",
            "sre",
            "platform engineer",
            "site reliability",
        )
    ):
        return "DevOps / Infrastructure"

    if any(
        key in text
        for key in (
            "product manager",
            "product lead",
        )
    ):
        return "Product"

    if any(
        key in text
        for key in (
            "designer",
            "ux",
            "ui",
        )
    ):
        return "Design"

    if any(
        key in text
        for key in (
            "marketing",
            "growth",
            "seo",
        )
    ):
        return "Marketing"

    if any(
        key in text
        for key in (
            "sales",
            "account executive",
            "business development",
        )
    ):
        return "Sales / Business"

    if "research" in text:
        return "Research"

    return "Other"


def build_record(
    job: dict[str, Any],
) -> dict[str, Any]:

    title = job.get(
        "title",
        "",
    ).strip()

    company = (
        job.get(
            "company",
            "",
        ).strip()
        or "Unknown Company"
    )

    description = (
        job.get(
            "content",
            "",
        ).strip()
        or job.get(
            "description",
            "",
        ).strip()
    )

    return {
        "schemaVersion": "1.0",
        "recordType": "JOB",
        "source": {
            "name": job[
                "source"
            ],
            "url": job.get(
                "finalUrl",
                job["url"],
            ),
        },
        "content": {
            "title": title,
            "company": company,
            "date": job[
                "publishedAt"
            ],
            "is_remote": bool(
                job.get(
                    "isRemote",
                    True,
                )
            ),
            "role_family": infer_role_family(
                title
            ),
            "url": job[
                "url"
            ],
            "full_text": description,
            "location": job.get(
                "location",
                "Remote",
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
    print("AI JOB PIPELINE")
    print("=" * 70)

    print(
        f"Sources configured: "
        f"{len(JOB_SOURCES)}"
    )

    for source in JOB_SOURCES:
        print(
            f" - {source}"
        )

    print()
    print(
        "Collecting jobs from "
        "the last 24 hours..."
    )

    jobs = await crawl_jobs(
        hours=24
    )

    records: list[
        dict[str, Any]
    ] = []

    rejections: list[
        dict[str, Any]
    ] = []

    for job in jobs:

        record = build_record(
            job
        )

        errors = (
            validate_job_record(
                record
            )
        )

        if errors:

            rejections.append(
                {
                    "url": job.get(
                        "url"
                    ),
                    "source": job.get(
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
        JOBS_FILE,
        records,
    )

    write_json(
        JOBS_REJECTIONS_FILE,
        rejections,
    )

    print()
    print("=" * 70)
    print("JOB PIPELINE RESULT")
    print("=" * 70)

    print(
        f"Jobs collected      : "
        f"{len(jobs)}"
    )

    print(
        f"Valid job records   : "
        f"{len(records)}"
    )

    print(
        f"Rejected            : "
        f"{len(rejections)}"
    )

    # Source breakdown.
    source_counts: dict[
        str,
        int,
    ] = {}

    for record in records:

        source_name = record[
            "source"
        ]["name"]

        source_counts[
            source_name
        ] = (
            source_counts.get(
                source_name,
                0,
            )
            + 1
        )

    print()
    print("SOURCE BREAKDOWN")

    for source in JOB_SOURCES:

        print(
            f"{source:20s}: "
            f"{source_counts.get(source, 0)}"
        )

    print()
    print(
        "Freshness window    : "
        "24 hours"
    )

    print(
        "Output              : "
        "data/jobs.json"
    )

    print(
        "Rejections          : "
        "data/job_rejections.json"
    )


if __name__ == "__main__":
    asyncio.run(main())