import asyncio
import aiohttp


PWC_URL = "https://paperswithcode.com/api/v1/papers/"


async def fetch_paper(
    session: aiohttp.ClientSession,
    arxiv_id: str,
) -> dict | None:
    """
    Fetch paper metadata from Papers With Code using an arXiv ID.
    """

    url = f"{PWC_URL}arxiv:{arxiv_id}"

    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=30),
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Intelligence-Pipeline/1.0",
        },
    ) as response:

        print(f"HTTP status: {response.status}")

        if response.status == 404:
            return None

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
        print("PAPERS WITH CODE TEST")
        print("=" * 70)

        if data is None:
            print("Paper not found in Papers With Code.")
            return

        print(data)


if __name__ == "__main__":
    asyncio.run(main())