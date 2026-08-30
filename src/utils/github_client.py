from __future__ import annotations

from typing import Any, Optional

import aiohttp

from src.utils.retry import retry_async


GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Async client for GitHub repository metadata."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: Optional[str] = None,
    ) -> None:
        self.session = session
        self.token = token

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    async def get_repository(
        self,
        owner: str,
        repo: str,
    ) -> Optional[dict[str, Any]]:

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

        async def request() -> Optional[dict[str, Any]]:

            async with self.session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status == 404:
                    return None

                response.raise_for_status()

                return await response.json()

        return await retry_async(request)