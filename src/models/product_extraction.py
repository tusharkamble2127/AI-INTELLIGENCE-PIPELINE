from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExtractedPricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"
    UNKNOWN = "UNKNOWN"


class ProductExtraction(BaseModel):
    startup_name: Optional[str] = None

    pricing_model: ExtractedPricingModel = (
        ExtractedPricingModel.UNKNOWN
    )

    startup_evidence: Optional[str] = None

    pricing_evidence: Optional[str] = None