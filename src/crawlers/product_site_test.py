from __future__ import annotations

import asyncio

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import (
    async_playwright,
)


PRODUCT_URL = (
    "https://www.producthunt.com/r/BLPV3H4S2Y7TQX"
)


def extract_text(html: str) -> str:
    """
    Remove HTML boilerplate and return readable text.
    """

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
        ]
    ):
        element.decompose()

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    return " ".join(text.split())


async def fetch_with_aiohttp(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[int, str, str]:
    """
    Try a lightweight asynchronous HTTP request first.
    """

    async with session.get(
        url,
        allow_redirects=True,
        timeout=aiohttp.ClientTimeout(total=30),
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
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as response:

        html = await response.text()

        return (
            response.status,
            str(response.url),
            html,
        )


async def fetch_with_playwright(
    url: str,
) -> tuple[str, str]:
    """
    Browser-based fallback for JS-heavy or blocked pages.
    """

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
        )

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            ),
        )

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Give client-side rendering a short opportunity
            # to populate the page.
            await page.wait_for_timeout(3000)

            html = await page.content()

            return page.url, html

        finally:

            await browser.close()


async def main() -> None:

    print("=" * 70)
    print("PRODUCT WEBSITE CRAWLER TEST")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:

        try:

            status, final_url, html = (
                await fetch_with_aiohttp(
                    session,
                    PRODUCT_URL,
                )
            )

            print(
                f"aiohttp status : {status}"
            )

            print(
                f"aiohttp URL    : {final_url}"
            )

            if 200 <= status < 400:

                print(
                    "aiohttp succeeded."
                )

            else:

                print(
                    "aiohttp could not access "
                    "the page."
                )

                print(
                    "Switching to Playwright..."
                )

                final_url, html = (
                    await fetch_with_playwright(
                        final_url
                    )
                )

                print(
                    "Playwright succeeded."
                )

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as exc:

            print(
                f"aiohttp error: {exc}"
            )

            print(
                "Switching to Playwright..."
            )

            final_url, html = (
                await fetch_with_playwright(
                    PRODUCT_URL
                )
            )

            print(
                "Playwright succeeded."
            )

    text = extract_text(html)

    print()
    print(
        f"Final URL    : {final_url}"
    )

    print(
        f"HTML size    : {len(html):,} characters"
    )

    print(
        f"Text size    : {len(text):,} characters"
    )

    print()
    print("EXTRACTED TEXT")
    print("-" * 70)
    print(text[:5000])


if __name__ == "__main__":
    asyncio.run(main())