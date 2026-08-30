from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

from src.crawlers.producthunt_crawler import (
    ProductHuntCrawler,
)
from src.processors.product_enricher import (
    ProductEnricher,
)
from src.processors.product_filter import (
    is_ai_product,
)
from src.processors.product_validator import (
    validate_product_record,
)


# ---------------------------------------------------------
# Batch configuration
# ---------------------------------------------------------

TARGET_PRODUCTS = 100
CONCURRENCY = 5

DATA_DIR = Path("data")

PRODUCTS_FILE = (
    DATA_DIR / "products.json"
)

REJECTIONS_FILE = (
    DATA_DIR / "product_rejections.json"
)

INFRASTRUCTURE_FILE = (
    DATA_DIR
    / "product_infrastructure_failures.json"
)


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def load_json_list(
    path: Path,
) -> list[dict[str, Any]]:
    """
    Load an existing JSON array.

    Missing or invalid files result in an empty list.
    """

    if not path.exists():
        return []

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return []


def write_json_list(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    """
    Write records as a formatted JSON array.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            indent=2,
            ensure_ascii=False,
        )


def normalize_text(
    value: Any,
) -> str:
    """
    Normalize text for duplicate detection.
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def product_identity(
    record: dict[str, Any],
) -> tuple[str, str]:
    """
    Build a stable product identity.

    Primary identity:
        Product Hunt source URL

    Secondary identity:
        normalized startup name
    """

    source = record.get(
        "source",
        {},
    )

    content = record.get(
        "content",
        {},
    )

    source_url = normalize_text(
        source.get("url")
    )

    startup_name = normalize_text(
        content.get("startupName")
    )

    return (
        source_url,
        startup_name,
    )


def merge_unique_records(
    existing: list[dict[str, Any]],
    new_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge records while preventing duplicates.

    Existing records are preserved.
    New unique records are appended.
    """

    merged: list[dict[str, Any]] = []

    seen_urls: set[str] = set()
    seen_names: set[str] = set()

    for record in (
        existing + new_records
    ):

        source, name = product_identity(
            record
        )

        # Prefer source URL as the strongest identity.
        if source and source in seen_urls:
            continue

        # If source URL is missing, fall back to
        # normalized startup name.
        if (
            not source
            and name
            and name in seen_names
        ):
            continue

        if source:
            seen_urls.add(source)

        if name:
            seen_names.add(name)

        merged.append(record)

    return merged


def is_provider_unavailable(
    result: dict[str, Any],
) -> bool:
    """
    Identify failures caused by all LLM providers
    being unavailable.

    These are infrastructure failures, not
    product-quality failures.
    """

    if result.get("reason") != (
        "enrichment_exception"
    ):
        return False

    error = str(
        result.get("error", "")
    ).lower()

    return (
        "all llm providers failed"
        in error
        or "temporarily unavailable"
        in error
        or "quota" in error
        or "rate limit" in error
    )


# ---------------------------------------------------------
# Enrichment worker
# ---------------------------------------------------------

async def enrich_with_limit(
    semaphore: asyncio.Semaphore,
    enricher: ProductEnricher,
    product: dict[str, Any],
) -> dict[str, Any]:

    product_name = product.get(
        "name",
        "Unknown Product",
    )

    try:

        async with semaphore:

            result = await enricher.enrich(
                product
            )

        if result is None:

            return {
                "status": "rejected",
                "product": product_name,
                "reason": (
                    "enrichment_returned_none"
                ),
            }

        return {
            "status": "enriched",
            "product": product_name,
            "record": result,
        }

    except Exception as exc:

        return {
            "status": "rejected",
            "product": product_name,
            "reason": "enrichment_exception",
            "error": str(exc),
        }


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

async def main() -> None:

    load_dotenv()

    token = os.getenv(
        "PRODUCT_HUNT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "PRODUCT_HUNT_TOKEN is missing "
            "from .env"
        )

    # -----------------------------------------------------
    # Load existing cumulative dataset
    # -----------------------------------------------------

    existing_products = load_json_list(
        PRODUCTS_FILE
    )

    existing_rejections = load_json_list(
        REJECTIONS_FILE
    )

    existing_infrastructure = (
        load_json_list(
            INFRASTRUCTURE_FILE
        )
    )

    print("=" * 70)
    print("PRODUCT BATCH PIPELINE")
    print("=" * 70)

    print(
        f"Existing valid products: "
        f"{len(existing_products)}"
    )

    # -----------------------------------------------------
    # Build known product identities
    # -----------------------------------------------------

    existing_urls: set[str] = set()
    existing_names: set[str] = set()

    for record in existing_products:

        source_url, startup_name = (
            product_identity(record)
        )

        if source_url:
            existing_urls.add(
                source_url
            )

        if startup_name:
            existing_names.add(
                startup_name
            )

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=10,
    )

    candidates: list[
        dict[str, Any]
    ] = []

    valid_records: list[
        dict[str, Any]
    ] = []

    rejected_records: list[
        dict[str, Any]
    ] = []

    infrastructure_failures: list[
        dict[str, Any]
    ] = []

    crawler: ProductHuntCrawler | None = None
    enricher: ProductEnricher | None = None

    try:

        async with aiohttp.ClientSession(
            connector=connector
        ) as session:

            crawler = ProductHuntCrawler(
                session=session,
                token=token,
            )

            enricher = ProductEnricher(
                session=session
            )

            semaphore = (
                asyncio.Semaphore(
                    CONCURRENCY
                )
            )

            # -------------------------------------------------
            # 1. Collect NEW AI candidates
            # -------------------------------------------------

            seen_candidate_ids: set[str] = set()
            seen_candidate_urls: set[str] = set()
            seen_candidate_names: set[str] = set()

            # Search more than target because some products
            # may already exist in the cumulative dataset.
            scan_limit = max(
                200,
                TARGET_PRODUCTS * 5,
            )

            async for product in (
                crawler.iter_products(
                    page_size=10,
                    max_products=scan_limit,
                )
            ):

                if not is_ai_product(
                    product
                ):
                    continue

                product_id = normalize_text(
                    product.get("id")
                )

                product_url = normalize_text(
                    product.get("url")
                )

                product_name = normalize_text(
                    product.get("name")
                )

                # ---------------------------------------------
                # Skip candidates already present in dataset
                # ---------------------------------------------

                if (
                    product_url
                    and product_url in existing_urls
                ):
                    continue

                if (
                    not product_url
                    and product_name
                    and product_name
                    in existing_names
                ):
                    continue

                # ---------------------------------------------
                # Skip duplicates in current scan
                # ---------------------------------------------

                if (
                    product_id
                    and product_id
                    in seen_candidate_ids
                ):
                    continue

                if (
                    product_url
                    and product_url
                    in seen_candidate_urls
                ):
                    continue

                if (
                    product_name
                    and product_name
                    in seen_candidate_names
                ):
                    continue

                if product_id:
                    seen_candidate_ids.add(
                        product_id
                    )

                if product_url:
                    seen_candidate_urls.add(
                        product_url
                    )

                if product_name:
                    seen_candidate_names.add(
                        product_name
                    )

                candidates.append(
                    product
                )

                if (
                    len(candidates)
                    >= TARGET_PRODUCTS
                ):
                    break

            print(
                f"New AI candidates selected: "
                f"{len(candidates)}"
            )

            # -------------------------------------------------
            # 2. Enrich candidates
            # -------------------------------------------------

            tasks = [
                asyncio.create_task(
                    enrich_with_limit(
                        semaphore=semaphore,
                        enricher=enricher,
                        product=product,
                    )
                )
                for product in candidates
            ]

            results = (
                await asyncio.gather(
                    *tasks
                )
                if tasks
                else []
            )

            # -------------------------------------------------
            # 3. Process enrichment results
            # -------------------------------------------------

            for result in results:

                # ---------------------------------------------
                # Provider/infrastructure failure
                # ---------------------------------------------

                if is_provider_unavailable(
                    result
                ):

                    infrastructure_failures.append(
                        {
                            "product": result.get(
                                "product"
                            ),
                            "reason": (
                                "provider_unavailable"
                            ),
                            "error": result.get(
                                "error"
                            ),
                        }
                    )

                    continue

                # ---------------------------------------------
                # Normal rejection
                # ---------------------------------------------

                if (
                    result.get("status")
                    != "enriched"
                ):

                    rejected_records.append(
                        result
                    )

                    continue

                record = result[
                    "record"
                ]

                errors = (
                    validate_product_record(
                        record
                    )
                )

                if errors:

                    rejected_records.append(
                        {
                            "status": "rejected",
                            "product": result[
                                "product"
                            ],
                            "reason": (
                                "validation_failed"
                            ),
                            "errors": errors,
                        }
                    )

                    continue

                valid_records.append(
                    record
                )

    finally:

        # -----------------------------------------------------
        # Always close Playwright/browser resources
        # -----------------------------------------------------

        if (
            enricher is not None
            and hasattr(
                enricher,
                "crawler",
            )
        ):

            try:

                await enricher.crawler.close()

            except Exception as exc:

                print(
                    "Warning: failed to close "
                    f"product crawler cleanly: {exc}"
                )

    # ---------------------------------------------------------
    # 4. Merge new records into cumulative dataset
    # ---------------------------------------------------------

    cumulative_products = (
        merge_unique_records(
            existing_products,
            valid_records,
        )
    )

    cumulative_rejections = (
        merge_unique_records(
            existing_rejections,
            rejected_records,
        )
    )

    cumulative_infrastructure = (
        merge_unique_records(
            existing_infrastructure,
            infrastructure_failures,
        )
    )

    # ---------------------------------------------------------
    # 5. Save cumulative outputs
    # ---------------------------------------------------------

    write_json_list(
        PRODUCTS_FILE,
        cumulative_products,
    )

    write_json_list(
        REJECTIONS_FILE,
        cumulative_rejections,
    )

    write_json_list(
        INFRASTRUCTURE_FILE,
        cumulative_infrastructure,
    )

    # ---------------------------------------------------------
    # 6. Final summary
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("PRODUCT BATCH RESULT")
    print("=" * 70)

    print(
        f"Batch candidates          : "
        f"{len(candidates)}"
    )

    print(
        f"Batch valid products      : "
        f"{len(valid_records)}"
    )

    print(
        f"Batch data-quality rejects: "
        f"{len(rejected_records)}"
    )

    print(
        f"Batch provider failures   : "
        f"{len(infrastructure_failures)}"
    )

    print()

    print(
        f"Cumulative valid products: "
        f"{len(cumulative_products)}"
    )

    print(
        f"Cumulative target        : "
        f"1000"
    )

    remaining = max(
        0,
        1000 - len(cumulative_products),
    )

    print(
        f"Remaining to target      : "
        f"{remaining}"
    )

    print()

    print(
        "Products output          : "
        "data/products.json"
    )

    print(
        "Rejections output        : "
        "data/product_rejections.json"
    )

    print(
        "Infrastructure output   : "
        "data/product_infrastructure_failures.json"
    )

    # ---------------------------------------------------------
    # 7. Batch rejection details
    # ---------------------------------------------------------

    if rejected_records:

        print()
        print(
            "BATCH DATA-QUALITY REJECTIONS"
        )
        print("-" * 70)

        for item in rejected_records:

            print(
                f"Product : "
                f"{item.get('product')}"
            )

            print(
                f"Reason  : "
                f"{item.get('reason')}"
            )

            if item.get("error"):
                print(
                    f"Error   : "
                    f"{item.get('error')}"
                )

            if item.get("errors"):
                print(
                    f"Errors  : "
                    f"{item.get('errors')}"
                )

            print("-" * 70

        )

    # ---------------------------------------------------------
    # 8. Batch infrastructure summary
    # ---------------------------------------------------------

    if infrastructure_failures:

        print()
        print(
            "BATCH PROVIDER FAILURES"
        )
        print("-" * 70)

        for item in (
            infrastructure_failures
        ):

            print(
                f"Product : "
                f"{item.get('product')}"
            )

            print(
                "Reason  : provider_unavailable"
            )

            print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())