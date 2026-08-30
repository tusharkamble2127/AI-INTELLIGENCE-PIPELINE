from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def validate_job_record(
    record: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    if record.get(
        "schemaVersion"
    ) != "1.0":
        errors.append(
            "invalid_schema_version"
        )

    if record.get(
        "recordType"
    ) != "JOB":
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

    if not source.get(
        "name"
    ):
        errors.append(
            "missing_source_name"
        )

    if not source.get(
        "url"
    ):
        errors.append(
            "missing_source_url"
        )

    if not content.get(
        "title"
    ):
        errors.append(
            "missing_title"
        )

    if not content.get(
        "company"
    ):
        errors.append(
            "missing_company"
        )

    if not content.get(
        "url"
    ):
        errors.append(
            "missing_job_url"
        )

    published = content.get(
        "date"
    )

    if not published:

        errors.append(
            "missing_date"
        )

    else:

        try:

            published_at = (
                datetime.fromisoformat(
                    published.replace(
                        "Z",
                        "+00:00",
                    )
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
                - timedelta(
                    hours=24
                )
            )

            if published_at < cutoff:
                errors.append(
                    "older_than_24_hours"
                )

        except ValueError:

            errors.append(
                "invalid_date"
            )

    # RSS/API description is accepted as the
    # full-text fallback when the source blocks
    # direct page crawling.
    if not content.get(
        "full_text"
    ):

        errors.append(
            "missing_full_text"
        )

    return errors