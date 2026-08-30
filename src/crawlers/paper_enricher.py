from __future__ import annotations

import asyncio
import os
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp
from dotenv import load_dotenv

from src.crawlers.arxiv_crawler import (
    fetch_arxiv,
    parse_arxiv_entries,
)
from src.models.entities import ResearchPaperEntity
from src.utils.github_client import GitHubClient
from src.utils.retry import retry_async


load_dotenv()

HF_PAPER_API = "https://huggingface.co/api/papers"


async def fetch_huggingface_paper(
    session: aiohttp.ClientSession,
    arxiv_id: str,
) -> Optional[dict[str, Any]]:
    """
    Fetch structured paper metadata from Hugging Face.

    Includes retry handling for:
        - 408 Request Timeout
        - 429 Rate Limit
        - 5xx Server Errors
        - network failures
        - timeouts
    """

    url = f"{HF_PAPER_API}/{arxiv_id}"

    async def request() -> Optional[dict[str, Any]]:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Intelligence-Pipeline/1.0",
            },
        ) as response:

            if response.status == 404:
                return None

            response.raise_for_status()

            return await response.json()

    return await retry_async(request)


def extract_arxiv_id(paper_url: str) -> str:
    """
    Convert an arXiv URL into an arXiv ID.

    Example:
        https://arxiv.org/abs/2608.26105v1
        -> 2608.26105
    """

    arxiv_id = paper_url.rstrip("/").split("/")[-1]

    if arxiv_id.startswith("arXiv:"):
        arxiv_id = arxiv_id.replace("arXiv:", "", 1)

    if "v" in arxiv_id:
        arxiv_id = arxiv_id.rsplit("v", 1)[0]

    return arxiv_id


def parse_github_url(
    github_url: str,
) -> tuple[str, str]:
    """
    Extract GitHub owner and repository name.

    Example:
        https://github.com/Video-Reason/VBVR-Pro
        -> ("Video-Reason", "VBVR-Pro")
    """

    parsed = urlparse(github_url)

    if parsed.netloc.lower() not in {
        "github.com",
        "www.github.com",
    }:
        raise ValueError(
            f"Not a GitHub URL: {github_url}"
        )

    parts = [
        part
        for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) < 2:
        raise ValueError(
            f"Invalid GitHub repository URL: {github_url}"
        )

    owner = parts[0]
    repo = parts[1].removesuffix(".git")

    return owner, repo


async def enrich_paper(
    paper: ResearchPaperEntity,
    session: aiohttp.ClientSession,
    github: GitHubClient,
) -> ResearchPaperEntity:
    """
    Enrich an ArXiv paper with:

        ArXiv
          ↓
        Hugging Face
          ↓
        verified GitHub repository
          ↓
        live GitHub star count

    If no verified GitHub repository exists,
    github_url and github_stars remain None.
    """

    arxiv_id = extract_arxiv_id(
        str(paper.paper_url)
    )

    try:
        hf_data = await fetch_huggingface_paper(
            session=session,
            arxiv_id=arxiv_id,
        )

    except Exception as exc:
        print(
            f"Warning: Hugging Face lookup failed "
            f"for {arxiv_id}: {exc}"
        )
        return paper

    if not hf_data:
        return paper

    github_url = hf_data.get("githubRepo")

    if not github_url:
        return paper

    try:
        owner, repo = parse_github_url(
            github_url
        )

        repository = await github.get_repository(
            owner=owner,
            repo=repo,
        )

        if repository is None:
            return paper

        paper.github_url = repository.get(
            "html_url"
        )

        paper.github_stars = repository.get(
            "stargazers_count"
        )

    except (ValueError, KeyError, TypeError) as exc:
        print(
            f"Warning: Could not resolve GitHub "
            f"repository for {arxiv_id}: {exc}"
        )

    return paper


async def main() -> None:
    """
    End-to-end test:

        ArXiv
          ↓
        Hugging Face
          ↓
        GitHub API
          ↓
        live stars
    """

    token = os.getenv("GITHUB_TOKEN")

    connector = aiohttp.TCPConnector(
        limit=50,
        limit_per_host=20,
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        github = GitHubClient(
            session=session,
            token=token,
        )

        raw_xml = await fetch_arxiv(
            session=session,
            search_query="cat:cs.AI",
            start=0,
            max_results=5,
        )

        papers = parse_arxiv_entries(
            raw_xml
        )

        print("=" * 70)
        print("PAPER ENRICHMENT TEST")
        print("=" * 70)

        for index, paper in enumerate(
            papers,
            start=1,
        ):

            enriched = await enrich_paper(
                paper=paper,
                session=session,
                github=github,
            )

            print(f"\nPaper {index}")
            print(
                f"Title       : "
                f"{enriched.title}"
            )
            print(
                f"Paper URL   : "
                f"{enriched.paper_url}"
            )
            print(
                f"GitHub URL  : "
                f"{enriched.github_url}"
            )
            print(
                f"GitHub Stars: "
                f"{enriched.github_stars}"
            )
            print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())