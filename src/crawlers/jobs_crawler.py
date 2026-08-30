from __future__ import annotations
import asyncio
import email.utils
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup


JOB_SOURCES = {
    "Remote OK": {
        "type": "json",
        "url": "https://remoteok.com/api",
    },
    "We Work Remotely": {
        "type": "rss",
        "url": "https://weworkremotely.com/remote-jobs.rss",
    },
    "Himalayas": {
        "type": "rss",
        "url": "https://himalayas.app/jobs/rss",
    },
    "Jobicy": {
        "type": "rss",
        "url": "https://jobicy.com/jobs/feed",
    },
    "RemoteFirstJobs": {
        "type": "rss",
        "url": "https://remotefirstjobs.com/rss/jobs/ai.rss",
    },
}


AI_KEYWORDS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml engineer",
    "mlops",
    "deep learning",
    "generative ai",
    "genai",
    "llm",
    "large language model",
    "nlp",
    "computer vision",
    "data scientist",
    "data science",
    "ai engineer",
    "machine learning engineer",
    "applied scientist",
    "research scientist",
    "prompt engineer",
    "ai agent",
    "agents",
    "robotics",
)


def clean_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    soup = BeautifulSoup(
        value,
        "html.parser",
    )

    return " ".join(
        soup.get_text(
            " ",
            strip=True,
        ).split()
    )


def parse_datetime(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    value = value.strip()

    try:
        parsed = email.utils.parsedate_to_datetime(
            value
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        pass

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except ValueError:
        return None


def is_ai_job(
    title: str,
    description: str,
) -> bool:

    text = (
        f"{title} {description}"
    ).lower()

    return any(
        keyword in text
        for keyword in AI_KEYWORDS
    )


def get_child_text(
    element: ET.Element,
    names: tuple[str, ...],
) -> str:

    for child in list(element):

        tag = child.tag

        if "}" in tag:
            tag = tag.split(
                "}",
                1,
            )[1]

        if tag.lower() in names:
            return (
                child.text or ""
            ).strip()

    return ""


def get_link(
    element: ET.Element,
) -> str:

    for child in list(element):

        tag = child.tag

        if "}" in tag:
            tag = tag.split(
                "}",
                1,
            )[1]

        if tag.lower() != "link":
            continue

        href = child.attrib.get(
            "href"
        )

        if href:
            return href.strip()

        if child.text:
            return child.text.strip()

    return ""


def infer_company(
    title: str,
    description: str,
) -> str:

    title = clean_text(
        title
    )

    # Common separators used by remote-job feeds.
    for separator in (
        " • ",
        " | ",
        " — ",
        " – ",
        " at ",
    ):
        if separator in title:

            parts = [
                part.strip()
                for part in title.split(
                    separator,
                    1,
                )
            ]

            if len(parts) == 2:
                left, right = parts

                if left and right:
                    return right

    # Try a few common description patterns.
    text = clean_text(
        description
    )

    lowered = text.lower()

    markers = (
        "company:",
        "company -",
        "employer:",
        "at ",
    )

    for marker in markers:

        index = lowered.find(
            marker
        )

        if index >= 0:

            candidate = text[
                index
                + len(marker):
            ].strip()

            if candidate:

                candidate = candidate.split(
                    "\n",
                    1,
                )[0].strip()

                if len(candidate) <= 100:
                    return candidate

    return "Unknown Company"


def parse_rss(
    xml_text: str,
    source_name: str,
    cutoff: datetime,
) -> list[dict[str, Any]]:

    root = ET.fromstring(
        xml_text
    )

    results: list[
        dict[str, Any]
    ] = []

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

        title = get_child_text(
            element,
            ("title",),
        )

        description = get_child_text(
            element,
            (
                "description",
                "summary",
                "content",
                "encoded",
            ),
        )

        url = get_link(
            element
        )

        published_raw = get_child_text(
            element,
            (
                "pubdate",
                "published",
                "updated",
                "date",
                "created",
            ),
        )

        published_at = parse_datetime(
            published_raw
        )

        if not published_at:
            continue

        if published_at < cutoff:
            continue

        description = clean_text(
            description
        )

        if not is_ai_job(
            title,
            description,
        ):
            continue

        company = infer_company(
            title,
            description,
        )

        results.append(
            {
                "source": source_name,
                "title": clean_text(
                    title
                ),
                "url": url,
                "description": description,
                "company": company,
                "location": "Remote",
                "publishedAt": (
                    published_at.isoformat()
                ),
                "isRemote": True,
            }
        )

    return results


def parse_remote_ok(
    payload: Any,
    cutoff: datetime,
) -> list[dict[str, Any]]:

    results: list[
        dict[str, Any]
    ] = []

    if not isinstance(
        payload,
        list,
    ):
        return results

    for item in payload:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get("legal"):
            continue

        title = str(
            item.get(
                "position",
                item.get(
                    "title",
                    "",
                ),
            )
        ).strip()

        description = clean_text(
            str(
                item.get(
                    "description",
                    "",
                )
            )
        )

        if not is_ai_job(
            title,
            description,
        ):
            continue

        published_raw = (
            item.get("date")
            or item.get("epoch")
        )

        published_at: datetime | None = None

        if isinstance(
            published_raw,
            (int, float),
        ):

            try:
                published_at = (
                    datetime.fromtimestamp(
                        published_raw,
                        tz=timezone.utc,
                    )
                )
            except (
                ValueError,
                OSError,
                OverflowError,
            ):
                published_at = None

        else:

            published_at = parse_datetime(
                str(
                    published_raw
                )
                if published_raw
                else None
            )

        if not published_at:
            continue

        if published_at < cutoff:
            continue

        url = str(
            item.get(
                "url",
                "",
            )
        ).strip()

        if not url:
            continue

        company = str(
            item.get(
                "company",
                "",
            )
        ).strip()

        if not company:
            company = infer_company(
                title,
                description,
            )

        results.append(
            {
                "source": "Remote OK",
                "title": title,
                "url": url,
                "description": description,
                "company": company,
                "location": str(
                    item.get(
                        "location",
                        "Remote",
                    )
                ).strip(),
                "publishedAt": (
                    published_at.isoformat()
                ),
                "isRemote": True,
            }
        )

    return results


async def fetch_source(
    session: aiohttp.ClientSession,
    source_name: str,
    config: dict[str, str],
    cutoff: datetime,
) -> list[dict[str, Any]]:

    headers = {
        "User-Agent": (
            "AI-Intelligence-Pipeline/1.0"
        ),
        "Accept": (
            "application/json,"
            "application/rss+xml,"
            "application/xml,"
            "text/xml"
        ),
    }

    try:

        async with session.get(
            config["url"],
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=20
            ),
        ) as response:

            response.raise_for_status()

            if config["type"] == "json":

                payload = await response.json()

                return parse_remote_ok(
                    payload,
                    cutoff,
                )

            xml_text = await response.text()

            return parse_rss(
                xml_text,
                source_name,
                cutoff,
            )

    except Exception as exc:

        print(
            f"[JOBS] {source_name} failed: "
            f"{exc}"
        )

        return []


async def fetch_job_text(
    session: aiohttp.ClientSession,
    job: dict[str, Any],
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
            job["url"],
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=15
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

        main = (
            soup.find("article")
            or soup.find("main")
            or soup.body
        )

        page_text = (
            main.get_text(
                " ",
                strip=True,
            )
            if main
            else ""
        )

        page_text = " ".join(
            page_text.split()
        )

        # IMPORTANT:
        # RSS/API description is a legitimate fallback
        # when the job page cannot be fetched.
        if not page_text:
            page_text = clean_text(
                job.get(
                    "description",
                    "",
                )
            )

        job["content"] = (
            page_text
        )

        job["finalUrl"] = str(
            response.url
        )

        job["crawlMethod"] = (
            "aiohttp"
        )

        return job

    except Exception as exc:

        # Do NOT throw the job away just because
        # the listing page blocks us.
        fallback_text = clean_text(
            job.get(
                "description",
                "",
            )
        )

        job["content"] = (
            fallback_text
        )

        job["finalUrl"] = job.get(
            "url",
            "",
        )

        job["crawlError"] = str(
            exc
        )

        job["crawlMethod"] = (
            "rss_fallback"
        )

        return job


async def crawl_jobs(
    hours: int = 24,
) -> list[dict[str, Any]]:

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=5,
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        source_tasks = [
            fetch_source(
                session,
                source_name,
                config,
                cutoff,
            )
            for source_name, config
            in JOB_SOURCES.items()
        ]

        source_results = (
            await asyncio.gather(
                *source_tasks
            )
        )

        candidates: list[
            dict[str, Any]
        ] = []

        for result in source_results:
            candidates.extend(
                result
            )

        unique: dict[
            str,
            dict[str, Any],
        ] = {}

        for job in candidates:

            url = job.get(
                "url"
            )

            if not url:
                continue

            unique[url] = job

        jobs = list(
            unique.values()
        )

        semaphore = asyncio.Semaphore(
            10
        )

        async def enrich_one(
            job: dict[str, Any],
        ) -> dict[str, Any]:

            async with semaphore:
                return await fetch_job_text(
                    session,
                    job,
                )

        jobs = await asyncio.gather(
            *[
                enrich_one(job)
                for job in jobs
            ]
        )

    return jobs