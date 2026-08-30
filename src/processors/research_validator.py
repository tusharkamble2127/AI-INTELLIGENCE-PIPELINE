from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


INPUT_FILE = Path("data/research_papers.json")


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value)

    return parsed.scheme in {"http", "https"} and bool(
        parsed.netloc
    )


def main() -> None:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {INPUT_FILE}"
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        records = json.load(file)

    print("=" * 70)
    print("RESEARCH DATA QUALITY AUDIT")
    print("=" * 70)

    print(f"Total records: {len(records)}")

    errors = []

    paper_urls = set()
    titles = set()

    for index, record in enumerate(
        records,
        start=1,
    ):

        content = record.get(
            "content",
            {},
        )

        title = content.get(
            "title"
        )

        authors = content.get(
            "authors"
        )

        paper_url = content.get(
            "paper_url"
        )

        github_url = content.get(
            "github_url"
        )

        github_stars = content.get(
            "github_stars"
        )

        published_date = content.get(
            "published_date"
        )

        # Required title
        if not title:
            errors.append(
                f"Record {index}: missing title"
            )

        # Authors
        if not isinstance(
            authors,
            list,
        ) or not authors:
            errors.append(
                f"Record {index}: invalid authors"
            )

        # Paper URL
        if not paper_url or not is_valid_url(
            paper_url
        ):
            errors.append(
                f"Record {index}: invalid paper URL"
            )

        # Duplicate paper URL
        if paper_url in paper_urls:
            errors.append(
                f"Record {index}: duplicate paper URL"
            )

        paper_urls.add(paper_url)

        # Duplicate title
        if title in titles:
            errors.append(
                f"Record {index}: duplicate title"
            )

        titles.add(title)

        # GitHub validation
        if github_url is not None:

            if not is_valid_url(
                github_url
            ):
                errors.append(
                    f"Record {index}: invalid GitHub URL"
                )

            if (
                not isinstance(
                    github_stars,
                    int,
                )
                or github_stars < 0
            ):
                errors.append(
                    f"Record {index}: invalid GitHub stars"
                )

        # Published date
        if not published_date:
            errors.append(
                f"Record {index}: missing published date"
            )

    print()
    print(f"Unique paper URLs : {len(paper_urls)}")
    print(f"Unique titles     : {len(titles)}")
    print(f"Validation errors : {len(errors)}")

    github_records = sum(
        1
        for record in records
        if record.get("content", {}).get(
            "github_url"
        )
    )

    print(
        f"GitHub records    : {github_records}"
    )

    if errors:

        print()
        print("First 20 errors:")

        for error in errors[:20]:
            print(f"- {error}")

    else:

        print()
        print(
            "STATUS: DATASET PASSED BASIC QUALITY AUDIT"
        )


if __name__ == "__main__":
    main()