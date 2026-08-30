from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class RecordType(str, Enum):
    STARTUP = "STARTUP"
    PRODUCT = "PRODUCT"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    JOB = "JOB"
    NEWS = "NEWS"


class Source(BaseModel):
    name: str
    url: HttpUrl


class StartupData(BaseModel):
    employee_count: Optional[int] = Field(
        default=None,
        ge=0
    )


class StartupEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: RecordType = RecordType.STARTUP
    source: Source
    entity_name: str
    data: StartupData
    collected_at: datetime


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class ProductEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: RecordType = RecordType.PRODUCT
    source: Source
    startup_name: str
    pricing_model: PricingModel
    collected_at: datetime


class ResearchPaperEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: RecordType = RecordType.RESEARCH_PAPER
    title: str
    authors: List[str]
    paper_url: HttpUrl
    github_url: Optional[HttpUrl] = None
    github_stars: Optional[int] = Field(
        default=None,
        ge=0
    )
    published_date: datetime


class JobEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: RecordType = RecordType.JOB
    company: str
    date: datetime
    is_remote: bool
    role_family: str