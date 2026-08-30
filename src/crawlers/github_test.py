import asyncio
import os

import aiohttp
from dotenv import load_dotenv

from src.utils.github_client import GitHubClient


load_dotenv()


async def main() -> None:
    token = os.getenv("GITHUB_TOKEN")

    async with aiohttp.ClientSession() as session:

        github = GitHubClient(
            session=session,
            token=token,
        )

        repository = await github.get_repository(
            owner="huggingface",
            repo="transformers",
        )

        if repository is None:
            print("Repository not found.")
            return

        print("=" * 70)
        print("GITHUB API TEST")
        print("=" * 70)

        print(f"Repository : {repository['full_name']}")
        print(f"Stars      : {repository['stargazers_count']}")
        print(f"URL        : {repository['html_url']}")
        print(f"Updated    : {repository['updated_at']}")


if __name__ == "__main__":
    asyncio.run(main())