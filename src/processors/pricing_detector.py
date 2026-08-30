from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


PRICING_KEYWORDS = (
    "pricing",
    "plans",
    "plan",
    "subscription",
    "subscriptions",
    "billing",
    "upgrade",
    "packages",
    "membership",
)


def find_pricing_links(
    html: str,
    base_url: str,
) -> list[str]:
    """
    Find likely pricing-related links.

    Uses both anchor text and href so that pricing pages
    can be discovered even when the visible link text
    is not exactly 'Pricing'.
    """

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    candidates: list[tuple[int, str]] = []

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = str(
            anchor.get("href", "")
        ).strip()

        if not href:
            continue

        anchor_text = anchor.get_text(
            " ",
            strip=True,
        ).lower()

        href_lower = href.lower()

        combined = (
            f"{anchor_text} {href_lower}"
        )

        score = 0

        for keyword in PRICING_KEYWORDS:

            if keyword in anchor_text:
                score += 3

            if keyword in href_lower:
                score += 2

        if score > 0:

            absolute_url = urljoin(
                base_url,
                href,
            )

            candidates.append(
                (
                    score,
                    absolute_url,
                )
            )

    # Higher-confidence links first.
    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # Remove duplicates while preserving ranking.
    result: list[str] = []
    seen: set[str] = set()

    for _, url in candidates:

        if url in seen:
            continue

        seen.add(url)
        result.append(url)

    return result