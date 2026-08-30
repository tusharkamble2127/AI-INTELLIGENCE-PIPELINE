import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

import aiohttp

from src.models.entities import ResearchPaperEntity


ARXIV_API_URL = "https://export.arxiv.org/api/query"

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom"
}


async def fetch_arxiv(
    session: aiohttp.ClientSession,
    search_query: str = "cat:cs.AI",
    start: int = 0,
    max_results: int = 10,
) -> str:
    """
    Fetch raw Atom/XML data from the arXiv API asynchronously.
    """

    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with session.get(
        ARXIV_API_URL,
        params=params,
        timeout=timeout,
    ) as response:

        response.raise_for_status()

        return await response.text()


def parse_arxiv_entries(xml_text: str) -> List[ResearchPaperEntity]:
    """
    Parse arXiv Atom/XML response into ResearchPaperEntity objects.
    """

    root = ET.fromstring(xml_text)

    papers: List[ResearchPaperEntity] = []

    for entry in root.findall("atom:entry", ATOM_NS):

        title_element = entry.find("atom:title", ATOM_NS)
        published_element = entry.find("atom:published", ATOM_NS)
        id_element = entry.find("atom:id", ATOM_NS)

        if (
            title_element is None
            or published_element is None
            or id_element is None
        ):
            continue

        title = " ".join(
            title_element.text.split()
        )

        paper_url = id_element.text.strip()

        authors = []

        for author in entry.findall("atom:author", ATOM_NS):

            name_element = author.find("atom:name", ATOM_NS)

            if name_element is not None and name_element.text:
                authors.append(name_element.text.strip())

        published_date = datetime.fromisoformat(
            published_element.text.replace("Z", "+00:00")
        )

        paper = ResearchPaperEntity(
            title=title,
            authors=authors,
            paper_url=paper_url,
            github_url=None,
            github_stars=None,
            published_date=published_date,
        )

        papers.append(paper)

    return papers


async def main() -> None:
    """
    Fetch and parse recent AI research papers from arXiv.
    """

    async with aiohttp.ClientSession() as session:

        raw_xml = await fetch_arxiv(
            session=session,
            search_query="cat:cs.AI",
            start=0,
            max_results=5,
        )

        papers = parse_arxiv_entries(raw_xml)

        print("=" * 70)
        print("ARXIV PARSER TEST")
        print("=" * 70)
        print(f"Raw response size : {len(raw_xml):,} characters")
        print(f"Papers parsed     : {len(papers)}")
        print()

        for index, paper in enumerate(papers, start=1):

            print(f"Paper {index}")
            print(f"Title       : {paper.title}")
            print(f"Authors     : {', '.join(paper.authors)}")
            print(f"Paper URL   : {paper.paper_url}")
            print(f"Published   : {paper.published_date.isoformat()}")
            print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())