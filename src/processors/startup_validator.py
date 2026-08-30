from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


INPUT_FILE = Path("data/startups.json")


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value)

    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
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
    print("STARTUP DATA QUALITY AUDIT")
    print("=" * 70)

    print(f"Total records: {len(records)}")

    errors: list[str] = []
    source_urls: set[str] = set()
    startup_names: set[str] = set()

    for index, record in enumerate(
        records,
        start=1,
    ):

        if record.get("schemaVersion") != "1.0":
            errors.append(
                f"Record {index}: invalid schemaVersion"
            )

        if record.get("recordType") != "STARTUP":
            errors.append(
                f"Record {index}: invalid recordType"
            )

        source = record.get("source", {})
        content = record.get("content", {})
        data = content.get("data", {})

        source_url = source.get("url")
        name = content.get("entityName")
        employee_count = data.get(
            "employeeCount"
        )
        collected_at = record.get(
            "collectedAt"
        )

        # Source URL
        if not source_url or not is_valid_url(
            source_url
        ):
            errors.append(
                f"Record {index}: invalid source URL"
            )

        if source_url in source_urls:
            errors.append(
                f"Record {index}: duplicate source URL"
            )

        source_urls.add(source_url)

        # Startup name
        if not name:
            errors.append(
                f"Record {index}: missing entityName"
            )

        normalized_name = (
            name.strip().lower()
            if isinstance(name, str)
            else ""
        )

        if normalized_name in startup_names:
            errors.append(
                f"Record {index}: duplicate startup name"
            )

        startup_names.add(normalized_name)

        # Employee count
        if employee_count is not None:

            if (
                not isinstance(
                    employee_count,
                    int,
                )
                or employee_count < 0
            ):
                errors.append(
                    f"Record {index}: invalid employeeCount"
                )

        # Collection timestamp
        if not collected_at:
            errors.append(
                f"Record {index}: missing collectedAt"
            )

    print()
    print(
        f"Unique source URLs : {len(source_urls)}"
    )
    print(
        f"Unique startup names: {len(startup_names)}"
    )
    print(
        f"Validation errors   : {len(errors)}"
    )

    if errors:

        print()
        print("First 20 errors:")

        for error in errors[:20]:
            print(f"- {error}")

    else:

        print()
        print(
            "STATUS: STARTUP DATASET PASSED BASIC QUALITY AUDIT"
        )


if __name__ == "__main__":
    main()