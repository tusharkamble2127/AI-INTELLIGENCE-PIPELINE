from __future__ import annotations

import asyncio
import os
from typing import Any

import aiohttp
from dotenv import load_dotenv

from src.crawlers.arxiv_crawler import (
    fetch_arxiv,
    parse_arxiv_entries,
)
from src.crawlers.paper_enricher import enrich_paper
from src.utils.data_writer import write_json_records
from src.utils.github_client import GitHubClient


load_dotenv()


CONCURRENCY = 10
BATCH_SIZE = 100
TARGET_PAPERS = 1000


async def enrich_with_limit(
    semaphore: asyncio.Semaphore,
    paper,
    session: aiohttp.ClientSession,
    github: GitHubClient,
):
    """
    Enrich a paper while respecting the concurrency limit.
    """

    async with semaphore:

        return await enrich_paper(
            paper=paper,
            session=session,
            github=github,
        )


async def fetch_and_enrich_batch(
    session: aiohttp.ClientSession,
    github: GitHubClient,
    start: int,
    batch_size: int,
):
    """
    Fetch and enrich one batch of research papers.
    """

    raw_xml = await fetch_arxiv(
        session=session,
        search_query="cat:cs.AI",
        start=start,
        max_results=batch_size,
    )

    papers = parse_arxiv_entries(raw_xml)

    semaphore = asyncio.Semaphore(
        CONCURRENCY
    )

    tasks = [
        asyncio.create_task(
            enrich_with_limit(
                semaphore=semaphore,
                paper=paper,
                session=session,
                github=github,
            )
        )
        for paper in papers
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    successful = []
    failures = []

    for paper, result in zip(
        papers,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):

            failures.append(
                {
                    "title": paper.title,
                    "error": str(result),
                }
            )

        else:

            successful.append(result)

    return successful, failures


def paper_to_output(
    paper,
) -> dict[str, Any]:
    """
    Convert internal Pydantic model
    to assignment-friendly JSON structure.
    """

    return {
        "schemaVersion": paper.schema_version,
        "recordType": paper.record_type.value,
        "content": {
            "title": paper.title,
            "authors": paper.authors,
            "paper_url": str(paper.paper_url),
            "github_url": (
                str(paper.github_url)
                if paper.github_url
                else None
            ),
            "github_stars": paper.github_stars,
            "published_date": (
                paper.published_date.isoformat()
            ),
        },
    }


async def main() -> None:

    token = os.getenv(
        "GITHUB_TOKEN"
    )

    connector = aiohttp.TCPConnector(
        limit=50,
        limit_per_host=20,
    )

    all_papers = []
    all_failures = []

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        github = GitHubClient(
            session=session,
            token=token,
        )

        start = 0

        while len(all_papers) < TARGET_PAPERS:

            print()
            print("=" * 70)
            print(
                f"Fetching batch starting at {start}"
            )
            print("=" * 70)

            papers, failures = (
                await fetch_and_enrich_batch(
                    session=session,
                    github=github,
                    start=start,
                    batch_size=BATCH_SIZE,
                )
            )

            if not papers:
                print(
                    "No additional papers returned."
                )
                break

            all_papers.extend(papers)
            all_failures.extend(failures)

            print(
                f"Batch papers : {len(papers)}"
            )
            print(
                f"Total papers : {len(all_papers)}"
            )
            print(
                f"Failures     : {len(failures)}"
            )

            start += BATCH_SIZE

            if len(papers) < BATCH_SIZE:
                print(
                    "Source returned fewer records "
                    "than requested. Stopping."
                )
                break

    # Prevent accidental overshoot.
    all_papers = all_papers[:TARGET_PAPERS]

    output_records = [
        paper_to_output(paper)
        for paper in all_papers
    ]

    write_json_records(
        filename="research_papers.json",
        records=output_records,
    )

    github_count = sum(
        1
        for paper in all_papers
        if paper.github_url is not None
    )

    print()
    print("=" * 70)
    print("FINAL RESEARCH DATASET")
    print("=" * 70)
    print(
        f"Total papers     : {len(all_papers)}"
    )
    print(
        f"With GitHub      : {github_count}"
    )
    print(
        f"Without GitHub   : "
        f"{len(all_papers) - github_count}"
    )
    print(
        f"Total failures   : "
        f"{len(all_failures)}"
    )
    print(
        "Output           : "
        "data/research_papers.json"
    )


if __name__ == "__main__":
    asyncio.run(main())