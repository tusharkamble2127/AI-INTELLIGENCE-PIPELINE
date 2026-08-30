from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"
    UNKNOWN = "UNKNOWN"


class PricingExtraction(BaseModel):
    pricing_model: PricingModel = PricingModel.UNKNOWN
    pricing_evidence: Optional[str] = None