from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProductEnrichmentResult:
    success: bool
    product: str
    record: dict[str, Any] | None = None
    reason: str | None = None
    error: str | None = None