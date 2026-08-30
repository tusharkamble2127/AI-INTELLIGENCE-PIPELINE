from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_DIR = Path("data")


def ensure_data_directory() -> None:
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def append_json_records(
    filename: str,
    records: list[dict[str, Any]],
) -> None:
    """
    Append records to a JSON file.

    Existing records are preserved.
    """

    ensure_data_directory()

    path = DATA_DIR / filename

    existing: list[dict[str, Any]] = []

    if path.exists():

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            try:
                existing = json.load(file)

            except json.JSONDecodeError:
                existing = []

    existing.extend(records)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            existing,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


def write_json_records(
    filename: str,
    records: list[dict[str, Any]],
) -> None:
    """
    Overwrite a JSON file with records.
    """

    ensure_data_directory()

    path = DATA_DIR / filename

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )