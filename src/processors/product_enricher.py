from __future__ import annotations
from src.models.pricing_extraction import (
    PricingExtraction,
    PricingModel,
)

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
from pydantic import ValidationError

from src.crawlers.product_site_crawler import (
    ProductSiteCrawler,
)
from src.llm.orchestrator import (
    LLMOrchestrator,
)
from src.llm.prompts import (
    PRODUCT_EXTRACTION_PROMPT,
    PRICING_EXTRACTION_PROMPT,
)
from src.models.pricing_extraction import (
    PricingExtraction,
)
from src.models.product_extraction import (
    ProductExtraction,
)
from src.processors.pricing_detector import (
    find_pricing_links,
)
from src.processors.pricing_validator import (
    infer_pricing_model,
)


class ProductEnricher:
    """
    Enrich a Product Hunt product with:

    - startup/company name
    - pricing information
    - deterministic pricing detection
    - LLM fallback only when necessary
    - evidence and crawl metadata
    """

    HOME_PRICING_SIGNALS = (
        "free",
        "free plan",
        "free tier",
        "pricing",
        "plans",
        "per month",
        "per year",
        "$",
        "€",
        "£",
    )

    MAX_STARTUP_TEXT = 5000
    MAX_PRICING_TEXT = 7000

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        self.session = session

        self.crawler = ProductSiteCrawler(
            session
        )

        self.llm = LLMOrchestrator()

    @classmethod
    def homepage_has_pricing_signal(
        cls,
        text: str,
    ) -> bool:
        """
        Cheap deterministic check for pricing-related
        evidence already present on the homepage.
        """

        normalized = text.lower()

        return any(
            signal in normalized
            for signal in cls.HOME_PRICING_SIGNALS
        )

    @staticmethod
    def compact_text(
        text: str,
        max_chars: int,
    ) -> str:
        """
        Reduce LLM payload size while preserving
        the beginning and end of the page text.

        The end of pricing pages often contains
        comparison tables, FAQs, and plan details.
        """

        text = text.strip()

        if len(text) <= max_chars:
            return text

        head_size = int(
            max_chars * 0.65
        )

        tail_size = (
            max_chars - head_size
        )

        return (
            text[:head_size]
            + "\n\n[...CONTENT TRUNCATED...]\n\n"
            + text[-tail_size:]
        )

    async def extract_product_info(
        self,
        text: str,
    ) -> ProductExtraction:
        """
        Extract startup information using LLM.
        """

        compacted = self.compact_text(
            text,
            self.MAX_STARTUP_TEXT,
        )

        prompt = PRODUCT_EXTRACTION_PROMPT.format(
            text=compacted
        )

        raw = await self.llm.generate(
            prompt,
            max_tokens=350,
        )

        data = json.loads(raw)

        return ProductExtraction.model_validate(
            data
        )

    async def extract_pricing_info(
        self,
        text: str,
    ) -> PricingExtraction:
        """
        Extract pricing information using LLM.
        """

        compacted = self.compact_text(
            text,
            self.MAX_PRICING_TEXT,
        )

        prompt = PRICING_EXTRACTION_PROMPT.format(
            text=compacted
        )

        raw = await self.llm.generate(
            prompt,
            max_tokens=250,
        )

        data = json.loads(raw)

        return PricingExtraction.model_validate(
            data
        )

    async def enrich(
        self,
        product: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Full product enrichment pipeline.

        Strategy:

        1. Crawl website.
        2. Find pricing links.
        3. Check homepage/pricing text deterministically.
        4. Extract startup name.
        5. Use LLM for pricing only when
           deterministic evidence is insufficient.
        6. Validate final pricing model.
        """

        website = product.get(
            "website"
        )

        if not website:
            return None

        # -------------------------------------------------
        # 1. Crawl product website
        # -------------------------------------------------

        try:
            website_result = (
                await self.crawler.fetch(
                    website
                )
            )
        except Exception:
            return None

        website_text = website_result.get(
            "text",
            "",
        )

        if not website_text.strip():
            return None

        # -------------------------------------------------
        # 2. Discover pricing pages FIRST
        # -------------------------------------------------

        pricing_links = find_pricing_links(
            html=website_result["html"],
            base_url=str(
                website_result["url"]
            ),
        )

        homepage_pricing_model = (
            infer_pricing_model(
                website_text
            )
        )

        homepage_has_pricing = (
            self.homepage_has_pricing_signal(
                website_text
            )
        )

        # -------------------------------------------------
        # 3. Extract startup information
        # -------------------------------------------------

        try:
            product_info = (
                await self.extract_product_info(
                    website_text
                )
            )
        except (
            json.JSONDecodeError,
            ValidationError,
        ):
            return None

        if not product_info.startup_name:
            return None

        # -------------------------------------------------
        # 4. If homepage already gives strong pricing
        # evidence, don't crawl or call pricing LLM.
        # -------------------------------------------------

        if (
            homepage_pricing_model
            != PricingModel.UNKNOWN
        ):
            return {
                "schemaVersion": "1.0",
                "recordType": "PRODUCT",
                "source": {
                    "name": "Product Hunt",
                    "url": product.get("url"),
                },
                "content": {
                    "startupName": (
                        product_info.startup_name
                    ),
                    "pricingModel": (
                        homepage_pricing_model.value
                    ),
                },
                "collectedAt": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "_evidence": {
                    "startupEvidence": (
                        product_info.startup_evidence
                    ),
                    "pricingEvidence": (
                        "Pricing classification "
                        "determined from explicit "
                        "homepage evidence."
                    ),
                    "productWebsite": (
                        website_result["url"]
                    ),
                    "pricingPageUrl": (
                        website_result["url"]
                    ),
                    "crawlMethod": (
                        website_result["method"]
                    ),
                    "pricingCrawlMethod": (
                        website_result["method"]
                    ),
                    "pricingTextLength": len(
                        website_text
                    ),
                    "pricingDetection": (
                        "deterministic_homepage"
                    ),
                },
            }

        # -------------------------------------------------
        # 5. No pricing page + no explicit homepage
        # pricing evidence => reject without pricing LLM
        # -------------------------------------------------

        if (
            not pricing_links
            and not homepage_has_pricing
        ):
            return None

        pricing_info: PricingExtraction | None = None

        pricing_result: dict[str, Any] | None = None

        pricing_text = ""

        # -------------------------------------------------
        # 6. Try only the best two pricing pages
        # -------------------------------------------------

        for pricing_url in pricing_links[:2]:

            try:
                candidate_result = (
                    await self.crawler.fetch(
                        pricing_url
                    )
                )
            except Exception:
                continue

            candidate_text = candidate_result.get(
                "text",
                "",
            )

            if not candidate_text.strip():
                continue

            # -------------------------------------------------
            # 6A. Deterministic pricing classification FIRST
            # -------------------------------------------------

            deterministic_model = (
                infer_pricing_model(
                    candidate_text
                )
            )

            if (
                deterministic_model
                != PricingModel.UNKNOWN
            ):
                pricing_info = (
                    PricingExtraction(
                        pricing_model=(
                            deterministic_model
                        ),
                        pricing_evidence=(
                            "Pricing model "
                            "determined from "
                            "explicit pricing-page "
                            "evidence."
                        ),
                    )
                )

                pricing_result = (
                    candidate_result
                )

                pricing_text = (
                    candidate_text
                )

                break

            # -------------------------------------------------
            # 6B. Only now use pricing LLM
            # -------------------------------------------------

            try:
                candidate_pricing = (
                    await self.extract_pricing_info(
                        candidate_text
                    )
                )
            except (
                json.JSONDecodeError,
                ValidationError,
            ):
                continue

            llm_model = (
                candidate_pricing.pricing_model
            )

            # Validate the LLM output again
            # against deterministic evidence.
            final_model = infer_pricing_model(
                candidate_text
            )

            if (
                final_model
                == PricingModel.UNKNOWN
            ):
                # We don't have enough evidence to
                # safely accept the LLM result.
                # Do NOT hallucinate.
                continue

            candidate_pricing.pricing_model = (
                final_model
            )

            pricing_info = (
                candidate_pricing
            )

            pricing_result = (
                candidate_result
            )

            pricing_text = candidate_text

            break

        # -------------------------------------------------
        # 7. Homepage fallback when it contains
        # pricing-related text but deterministic
        # classification was unavailable.
        # -------------------------------------------------

        if (
            pricing_info is None
            and homepage_has_pricing
        ):

            try:
                homepage_pricing = (
                    await self.extract_pricing_info(
                        website_text
                    )
                )
            except (
                json.JSONDecodeError,
                ValidationError,
            ):
                homepage_pricing = None

            if homepage_pricing is not None:

                final_model = (
                    infer_pricing_model(
                        website_text
                    )
                )

                if (
                    final_model
                    != PricingModel.UNKNOWN
                ):
                    homepage_pricing.pricing_model = (
                        final_model
                    )

                    pricing_info = (
                        homepage_pricing
                    )

                    pricing_result = (
                        website_result
                    )

                    pricing_text = (
                        website_text
                    )

        # -------------------------------------------------
        # 8. Require verified pricing
        # -------------------------------------------------

        if (
            pricing_info is None
            or pricing_result is None
            or pricing_info.pricing_model
            == PricingModel.UNKNOWN
        ):
            return None

        # -------------------------------------------------
        # 9. Final PRODUCT record
        # -------------------------------------------------

        return {
            "schemaVersion": "1.0",
            "recordType": "PRODUCT",
            "source": {
                "name": "Product Hunt",
                "url": product.get("url"),
            },
            "content": {
                "startupName": (
                    product_info.startup_name
                ),
                "pricingModel": (
                    pricing_info.pricing_model.value
                ),
            },
            "collectedAt": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "_evidence": {
                "startupEvidence": (
                    product_info.startup_evidence
                ),
                "pricingEvidence": (
                    pricing_info.pricing_evidence
                ),
                "productWebsite": (
                    website_result["url"]
                ),
                "pricingPageUrl": (
                    pricing_result["url"]
                ),
                "crawlMethod": (
                    website_result["method"]
                ),
                "pricingCrawlMethod": (
                    pricing_result["method"]
                ),
                "pricingTextLength": len(
                    pricing_text
                ),
                "pricingDetection": (
                    "deterministic"
                    if infer_pricing_model(
                        pricing_text
                    )
                    != PricingModel.UNKNOWN
                    else "llm_validated"
                ),
            },
        }