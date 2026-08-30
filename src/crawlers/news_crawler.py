from __future__ import annotations

import asyncio
import email.utils
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup


NEWS_SOURCES = {
    "TechCrunch AI": (
        "https://techcrunch.com/category/artificial-intelligence/feed/"
    ),
    "OpenAI News": (
        "https://openai.com/news/rss.xml"
    ),
    "Hugging Face Blog": (
        "https://huggingface.co/blog/feed.xml"
    ),
    "VentureBeat": (
        "https://venturebeat.com/feed/"
    ),
    "MIT Technology Review AI": (
        "https://www.technologyreview.com/topic/"
        "artificial-intelligence/feed"
    ),
}


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    value = value.strip()

    # RFC 2822 RSS dates
    try:
        parsed = email.utils.parsedate_to_datetime(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(timezone.utc)

    except (TypeError, ValueError, OverflowError):
        pass

    # ISO 8601
    try:
        normalized = value.replace(
            "Z",
            "+00:00",
        )

        parsed = datetime.fromisoformat(
            normalized
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(timezone.utc)

    except ValueError:
        return None


def strip_html(value: str) -> str:
    soup = BeautifulSoup(
        value or "",
        "html.parser",
    )

    return " ".join(
        soup.get_text(
            " ",
            strip=True,
        ).split()
    )


def child_text(
    element: ET.Element,
    names: tuple[str, ...],
) -> str:
    for child in list(element):
        tag = child.tag

        if "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag.lower() in names:
            return (
                child.text or ""
            ).strip()

    return ""


def child_link(
    element: ET.Element,
) -> str:
    for child in list(element):
        tag = child.tag

        if "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag.lower() != "link":
            continue

        href = child.attrib.get("href")

        if href:
            return href.strip()

        if child.text:
            return child.text.strip()

    return ""


def parse_feed(
    xml_text: str,
    source_name: str,
    cutoff: datetime,
) -> list[dict[str, Any]]:

    root = ET.fromstring(
        xml_text
    )

    articles: list[
        dict[str, Any]
    ] = []

    # Supports both RSS <item> and Atom <entry>.
    for element in root.iter():

        tag = element.tag

        if "}" in tag:
            tag = tag.split(
                "}",
                1,
            )[1]

        if tag.lower() not in {
            "item",
            "entry",
        }:
            continue

        title = child_text(
            element,
            ("title",),
        )

        link = child_link(
            element
        )

        if not link:
            continue

        description = child_text(
            element,
            (
                "description",
                "summary",
                "content",
            ),
        )

        published = child_text(
            element,
            (
                "pubdate",
                "published",
                "updated",
                "date",
            ),
        )

        published_at = parse_datetime(
            published
        )

        # Strict 24-hour freshness.
        if (
            published_at is None
            or published_at < cutoff
        ):
            continue

        articles.append(
            {
                "source": source_name,
                "url": link,
                "title": strip_html(title),
                "summary": strip_html(
                    description
                ),
                "publishedAt": (
                    published_at.isoformat()
                ),
            }
        )

    return articles


async def fetch_feed(
    session: aiohttp.ClientSession,
    source_name: str,
    feed_url: str,
    cutoff: datetime,
) -> list[dict[str, Any]]:

    headers = {
        "User-Agent": (
            "AI-Intelligence-Pipeline/1.0"
        ),
        "Accept": (
            "application/rss+xml,"
            "application/atom+xml,"
            "application/xml,text/xml"
        ),
    }

    try:
        async with session.get(
            feed_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=20
            ),
        ) as response:

            response.raise_for_status()

            xml_text = await response.text()

        return parse_feed(
            xml_text,
            source_name,
            cutoff,
        )

    except Exception as exc:

        print(
            f"[NEWS] {source_name} failed: "
            f"{exc}"
        )

        return []


async def fetch_article_text(
    session: aiohttp.ClientSession,
    article: dict[str, Any],
) -> dict[str, Any]:

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/151.0 Safari/537.36"
        )
    }

    try:
        async with session.get(
            article["url"],
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=20
            ),
            allow_redirects=True,
        ) as response:

            response.raise_for_status()

            html = await response.text()

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "nav",
                "footer",
                "header",
            ]
        ):
            element.decompose()

        article_node = (
            soup.find("article")
            or soup.find("main")
            or soup.body
        )

        text = (
            article_node.get_text(
                " ",
                strip=True,
            )
            if article_node
            else ""
        )

        article["content"] = (
            " ".join(text.split())
        )

        article["finalUrl"] = str(
            response.url
        )

        article["crawlMethod"] = (
            "aiohttp"
        )

        return article

    except Exception as exc:

        article["content"] = ""
        article["crawlError"] = str(
            exc
        )
        article["crawlMethod"] = (
            "aiohttp"
        )

        return article


async def crawl_news(
    hours: int = 24,
) -> list[dict[str, Any]]:

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(hours=hours)
    )

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=5,
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        feed_tasks = [
            fetch_feed(
                session,
                source_name,
                feed_url,
                cutoff,
            )
            for source_name, feed_url
            in NEWS_SOURCES.items()
        ]

        feed_results = await asyncio.gather(
            *feed_tasks
        )

        candidates: list[
            dict[str, Any]
        ] = []

        for result in feed_results:
            candidates.extend(
                result
            )

        # Deduplicate by article URL.
        unique: dict[
            str,
            dict[str, Any],
        ] = {}

        for article in candidates:

            url = article.get(
                "url"
            )

            if not url:
                continue

            unique[url] = article

        articles = list(
            unique.values()
        )

        # Full-text extraction.
        semaphore = asyncio.Semaphore(
            10
        )

        async def crawl_one(
            article: dict[str, Any],
        ) -> dict[str, Any]:

            async with semaphore:
                return await fetch_article_text(
                    session,
                    article,
                )

        articles = await asyncio.gather(
            *[
                crawl_one(article)
                for article in articles
            ]
        )

    return articles