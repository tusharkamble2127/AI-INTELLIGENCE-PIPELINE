from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import (
    Browser,
    async_playwright,
)


class ProductSiteCrawler:
    """
    Fast two-tier crawler.

    aiohttp is always attempted first.
    Playwright is used only when:
      - HTTP access fails
      - extracted text is too sparse

    A single Chromium browser is reused for the
    lifetime of the crawler.
    """

    MIN_TEXT_LENGTH = 500

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        self.session = session

        self._playwright = None
        self._browser: Browser | None = None

    @staticmethod
    def clean_text(
        html: str,
    ) -> str:

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "nav",
                "footer",
            ]
        ):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True,
        )

        return " ".join(
            text.split()
        )

    @classmethod
    def needs_browser_fallback(
        cls,
        status: int,
        text: str,
    ) -> bool:

        if status < 200 or status >= 400:
            return True

        return len(text.strip()) < cls.MIN_TEXT_LENGTH

    async def _get_browser(self) -> Browser:

        if self._browser is not None:
            return self._browser

        self._playwright = (
            await async_playwright().start()
        )

        self._browser = (
            await self._playwright.chromium.launch(
                headless=True,
            )
        )

        return self._browser

    async def fetch_http(
        self,
        url: str,
    ) -> tuple[int, str, str]:

        async with self.session.get(
            url,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(
                total=20,
            ),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/151.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": (
                    "en-US,en;q=0.9"
                ),
            },
        ) as response:

            html = await response.text()

            return (
                response.status,
                str(response.url),
                html,
            )

    async def fetch_browser(
        self,
        url: str,
    ) -> tuple[str, str]:

        browser = await self._get_browser()

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        )

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )

            # Give client-side rendering a short window.
            await page.wait_for_timeout(
                1500
            )

            html = await page.content()

            return (
                page.url,
                html,
            )

        finally:
            await page.close()

    async def fetch(
        self,
        url: str,
    ) -> dict:

        try:

            status, final_url, html = (
                await self.fetch_http(url)
            )

            text = self.clean_text(
                html
            )

            method = "aiohttp"

            if self.needs_browser_fallback(
                status=status,
                text=text,
            ):

                method = "playwright"

                final_url, html = (
                    await self.fetch_browser(
                        final_url
                    )
                )

                text = self.clean_text(
                    html
                )

            return {
                "url": final_url,
                "method": method,
                "status": status,
                "html": html,
                "text": text,
            }

        except Exception:
            raise

    async def close(self) -> None:

        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None