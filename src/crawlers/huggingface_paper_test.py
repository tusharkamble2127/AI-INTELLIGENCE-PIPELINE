import asyncio
import aiohttp


HF_PAPER_URL = "https://huggingface.co/papers"


async def fetch_paper(
    session: aiohttp.ClientSession,
    arxiv_id: str,
) -> str:
    """
    Fetch the Hugging Face paper page for an arXiv ID.
    """

    url = f"{HF_PAPER_URL}/{arxiv_id}"

    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=30),
        headers={
            "User-Agent": "AI-Intelligence-Pipeline/1.0",
        },
    ) as response:

        response.raise_for_status()

        return await response.text()


async def main() -> None:
    arxiv_id = "2608.26105"

    async with aiohttp.ClientSession() as session:

        html = await fetch_paper(
            session,
            arxiv_id,
        )

    print("=" * 70)
    print("HUGGING FACE PAPER TEST")
    print("=" * 70)
    print(f"HTML size: {len(html):,} characters")
    print()
    print(html[:2000])


if __name__ == "__main__":
    asyncio.run(main())