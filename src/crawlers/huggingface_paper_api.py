import asyncio
import aiohttp


HF_PAPER_API = "https://huggingface.co/api/papers"


async def fetch_paper(
    session: aiohttp.ClientSession,
    arxiv_id: str,
) -> dict:
    """
    Fetch structured Hugging Face paper metadata using an arXiv ID.
    """

    url = f"{HF_PAPER_API}/{arxiv_id}"

    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=30),
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Intelligence-Pipeline/1.0",
        },
    ) as response:

        print(f"HTTP status: {response.status}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")

        response.raise_for_status()

        return await response.json()


async def main() -> None:
    arxiv_id = "2608.26105"

    async with aiohttp.ClientSession() as session:

        data = await fetch_paper(
            session,
            arxiv_id,
        )

    print("=" * 70)
    print("HUGGING FACE STRUCTURED PAPER TEST")
    print("=" * 70)

    print(data)


if __name__ == "__main__":
    asyncio.run(main())