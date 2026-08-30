from __future__ import annotations

from typing import Any


async def diagnose_product_enrichment(
    enricher,
    product: dict[str, Any],
) -> dict[str, Any]:

    name = product.get(
        "name",
        "Unknown Product",
    )

    website = product.get("website")

    if not website:
        return {
            "product": name,
            "reason": "NO_WEBSITE",
        }

    try:
        website_result = await enricher.crawler.fetch(
            website
        )
    except Exception as exc:
        return {
            "product": name,
            "reason": "WEBSITE_FETCH_FAILED",
            "error": str(exc),
        }

    website_text = website_result.get(
        "text",
        "",
    )

    if not website_text.strip():
        return {
            "product": name,
            "reason": "EMPTY_WEBSITE_TEXT",
        }

    try:
        product_info = (
            await enricher.extract_product_info(
                website_text
            )
        )
    except Exception as exc:
        return {
            "product": name,
            "reason": "STARTUP_EXTRACTION_FAILED",
            "error": str(exc),
        }

    if not product_info.startup_name:
        return {
            "product": name,
            "reason": "STARTUP_NAME_MISSING",
        }

    from src.processors.pricing_detector import (
        find_pricing_links,
    )

    pricing_links = find_pricing_links(
        html=website_result["html"],
        base_url=str(
            website_result["url"]
        ),
    )

    if not pricing_links:
        return {
            "product": name,
            "reason": "NO_PRICING_PAGE",
        }

    for pricing_url in pricing_links[:3]:

        try:
            pricing_result = (
                await enricher.crawler.fetch(
                    pricing_url
                )
            )
        except Exception:
            continue

        pricing_text = pricing_result.get(
            "text",
            "",
        )

        if not pricing_text.strip():
            continue

        try:
            pricing_info = (
                await enricher.extract_pricing_info(
                    pricing_text
                )
            )

            from src.processors.pricing_validator import (
                validate_pricing_model,
            )

            validated_model = (
                validate_pricing_model(
                    model=pricing_info.pricing_model,
                    pricing_text=pricing_text,
                )
            )

            if validated_model.value == "UNKNOWN":
                continue

            return {
                "product": name,
                "reason": "ENRICHMENT_SUCCESS",
                "pricing_model": validated_model.value,
                "startup_name": product_info.startup_name,
            }

        except Exception:
            continue

    return {
        "product": name,
        "reason": "PRICING_UNRESOLVED",
    }