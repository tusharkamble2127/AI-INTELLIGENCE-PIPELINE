from __future__ import annotations

from urllib.parse import urlparse


ALLOWED_PRICING_MODELS = {
    "FREE",
    "FREEMIUM",
    "PAID",
    "ENTERPRISE",
}


def is_valid_url(
    value: str | None,
) -> bool:

    if not value:
        return False

    parsed = urlparse(value)

    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
    )


def validate_product_record(
    record: dict,
) -> list[str]:

    errors: list[str] = []

    if record.get("schemaVersion") != "1.0":
        errors.append(
            "Invalid schemaVersion"
        )

    if record.get("recordType") != "PRODUCT":
        errors.append(
            "Invalid recordType"
        )

    source = record.get(
        "source",
        {},
    )

    content = record.get(
        "content",
        {},
    )

    source_url = source.get("url")
    startup_name = content.get(
        "startupName"
    )
    pricing_model = content.get(
        "pricingModel"
    )

    if not is_valid_url(source_url):
        errors.append(
            "Invalid source URL"
        )

    if not startup_name:
        errors.append(
            "Missing startupName"
        )

    if pricing_model not in (
        ALLOWED_PRICING_MODELS
    ):
        errors.append(
            "Invalid pricingModel"
        )

    if not record.get("collectedAt"):
        errors.append(
            "Missing collectedAt"
        )

    return errors