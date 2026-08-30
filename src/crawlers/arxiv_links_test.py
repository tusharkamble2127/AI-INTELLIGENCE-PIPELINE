import asyncio
import xml.etree.ElementTree as ET

import aiohttp

from src.crawlers.arxiv_crawler import fetch_arxiv


ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom"
}


async def main() -> None:
    async with aiohttp.ClientSession() as session:

        raw_xml = await fetch_arxiv(
            session=session,
            search_query="cat:cs.AI",
            start=0,
            max_results=5,
        )

    root = ET.fromstring(raw_xml)

    print("=" * 70)
    print("ARXIV LINK INSPECTION")
    print("=" * 70)

    for index, entry in enumerate(
        root.findall("atom:entry", ATOM_NS),
        start=1,
    ):
        title_element = entry.find("atom:title", ATOM_NS)

        title = (
            " ".join(title_element.text.split())
            if title_element is not None and title_element.text
            else "Unknown"
        )

        print(f"\nPaper {index}")
        print(f"Title: {title}")

        for link in entry.findall("atom:link", ATOM_NS):

            print(
                f"  type={link.get('type')} "
                f"rel={link.get('rel')} "
                f"title={link.get('title')} "
                f"href={link.get('href')}"
            )


if __name__ == "__main__":
    asyncio.run(main())