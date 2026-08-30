from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.processors.entity_resolver import (
    resolve_entity,
)


DATA_DIR = Path("data")

PRODUCTS_FILE = (
    DATA_DIR / "products.json"
)

STARTUPS_FILE = (
    DATA_DIR / "startups.json"
)

MAPPING_FILE = (
    DATA_DIR / "entity_mapping.json"
)


def load_json_list(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        return []

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            list,
        ):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return []


def write_json(
    path: Path,
    data: Any,
) -> None:

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def main() -> None:

    print("=" * 70)
    print("ENTITY RESOLUTION PIPELINE")
    print("=" * 70)

    startup_records = load_json_list(
        STARTUPS_FILE
    )

    product_records = load_json_list(
        PRODUCTS_FILE
    )

    raw_names: set[str] = set()

    # -----------------------------------------------------
    # Startup names
    # -----------------------------------------------------

    for record in startup_records:

        content = record.get(
            "content",
            {},
        )

        name = (
            content.get(
                "entityName"
            )
            or content.get(
                "startupName"
            )
        )

        if name:
            raw_names.add(
                str(name).strip()
            )

    # -----------------------------------------------------
    # Product startup names
    # -----------------------------------------------------

    for record in product_records:

        content = record.get(
            "content",
            {},
        )

        name = content.get(
            "startupName"
        )

        if name:
            raw_names.add(
                str(name).strip()
            )

    mapping: list[
        dict[str, Any]
    ] = []

    resolved_count = 0
    unresolved_count = 0

    for raw_name in sorted(
        raw_names
    ):

        (
            canonical,
            confidence,
            method,
        ) = resolve_entity(
            raw_name
        )

        if method == "UNRESOLVED":
            unresolved_count += 1
        else:
            resolved_count += 1

        mapping.append(
            {
                "rawName": raw_name,
                "canonicalName": canonical,
                "confidence": round(
                    confidence,
                    4,
                ),
                "method": method,
            }
        )

    write_json(
        MAPPING_FILE,
        mapping,
    )

    print(
        f"Unique raw entities : "
        f"{len(raw_names)}"
    )

    print(
        f"Resolved            : "
        f"{resolved_count}"
    )

    print(
        f"Unresolved          : "
        f"{unresolved_count}"
    )

    print(
        f"Output              : "
        f"{MAPPING_FILE}"
    )


if __name__ == "__main__":
    main()