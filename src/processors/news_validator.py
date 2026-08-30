from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def validate_news_record(
    record: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    required = (
        "schemaVersion",
        "recordType",
        "source",
        "content",
        "collectedAt",
    )

    for field in required:
        if field not in record:
            errors.append(
                f"missing_{field}"
            )

    if record.get(
        "recordType"
    ) != "NEWS":
        errors.append(
            "invalid_record_type"
        )

    source = record.get(
        "source",
        {},
    )

    content = record.get(
        "content",
        {},
    )

    if not source.get("name"):
        errors.append(
            "missing_source_name"
        )

    if not source.get("url"):
        errors.append(
            "missing_source_url"
        )

    if not content.get("title"):
        errors.append(
            "missing_title"
        )

    if not content.get("url"):
        errors.append(
            "missing_article_url"
        )

    published = content.get(
        "publishedAt"
    )

    if not published:
        errors.append(
            "missing_published_date"
        )

    else:
        try:
            published_at = datetime.fromisoformat(
                published.replace(
                    "Z",
                    "+00:00",
                )
            )

            if published_at.tzinfo is None:
                published_at = published_at.replace(
                    tzinfo=timezone.utc
                )

            cutoff = (
                datetime.now(
                    timezone.utc
                )
                - timedelta(hours=24)
            )

            if published_at < cutoff:
                errors.append(
                    "older_than_24_hours"
                )

        except ValueError:
            errors.append(
                "invalid_published_date"
            )

    if not content.get("content"):
        errors.append(
            "missing_full_text"
        )

    return errors