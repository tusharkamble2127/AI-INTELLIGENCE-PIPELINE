# AI Intelligence Pipeline

A scalable, fault-tolerant intelligence ingestion pipeline for collecting,
normalizing, enriching, validating, and resolving AI ecosystem data across
startups, products, research papers, jobs, and news.

----------------------------------------------------------------------------------------------------------

## Overview

The AI Intelligence Pipeline continuously ingests intelligence from multiple
web sources and converts heterogeneous raw data into structured JSON records.

The system focuses on:

- asynchronous web crawling
- Product Hunt ingestion
- startup and product enrichment
- pricing detection
- research paper collection
- AI news ingestion
- AI job ingestion
- deterministic entity resolution
- LLM fallback orchestration
- retry and rate-limit handling
- deduplication and validation
- production-scale architecture

----------------------------------------------------------------------------------------------------------

## Architecture


                    ┌──────────────────────┐
                    │     Data Sources     │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
     Product Hunt          News Sources         Job Boards
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Async Crawling Layer │
                    │ aiohttp / Playwright │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Processing Layer     │
                    │ filtering / parsing  │
                    │ normalization        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ LLM Orchestrator     │
                    │ Gemini → Groq →      │
                    │ NVIDIA DeepSeek      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Validation + Entity  │
                    │ Resolution           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ JSON / Final Output  │
                    └──────────────────────┘

----------------------------------------------------------------------------------------------------------

## Data Flow / Pipeline Flow

Sources
  ↓
Crawlers
  ↓
Raw Data
  ↓
Filtering
  ↓
LLM Enrichment
  ↓
Validation
  ↓
Entity Resolution
  ↓
JSON / Google Sheet

----------------------------------------------------------------------------------------------------------

## Technology Stack

Python
aiohttp
Playwright
BeautifulSoup
Pydantic
Gemini
Groq
NVIDIA NIM / DeepSeek
asyncio
pytest
JSON
Google Sheets

----------------------------------------------------------------------------------------------------------

# Running the Project

## Activate the virtual environment:
.venv\Scripts\activate

## Run tests:
python -m pytest

## Run product pipeline:
python -m src.processors.product_pipeline

## Run bulk product pipeline:
python -m src.processors.product_bulk_pipeline

## Run news pipeline:
python -m src.processors.news_pipeline

## Run jobs pipeline:
python -m src.processors.jobs_pipeline

## Run entity resolution:
python -m src.processors.entity_resolution_pipeline

----------------------------------------------------------------------------------------------------------


## Testing
Run the complete test suite:
python -m pytest


Provider-specific tests are available under:
src/llm/

Examples include:
retry_test
provider_state_test
orchestrator_state_test
groq_provider_test
deepseek_provider_test
deepseek_fallback_test

These tests verify provider availability, retry classification, fallback behavior,
quota handling, and multi-provider orchestration.

----------------------------------------------------------------------------------------------------------

## Scalability

The architecture is designed to scale horizontally from thousands of records to
hundreds of thousands of records by increasing:

- crawler workers
- concurrent HTTP connections
- queue partitions
- LLM workers
- database capacity
- distributed deduplication storage

The application separates crawling, enrichment, validation, and persistence so
each layer can scale independently.

For very large workloads, additional crawler and LLM workers can be added without
changing the canonical record schemas or downstream processing logic.

----------------------------------------------------------------------------------------------------------

## Rate Limit and Error Handling

The pipeline is designed to handle temporary provider and source failures
gracefully.

Supported mechanisms include:

- HTTP 429 detection
- exponential backoff
- randomized jitter
- `Retry-After` handling
- provider cooldown states
- multi-provider LLM fallback
- temporary network error retries
- separation of infrastructure failures from data-quality failures

Typical LLM fallback flow:

Gemini
   ↓
Groq
   ↓
NVIDIA NIM / DeepSeek

----------------------------------------------------------------------------------------------------------

## Context Window Protection

Large web pages are compacted before being sent to an LLM.

The pipeline uses:

- content truncation
- head/tail preservation
- bounded prompt sizes
- batch-based extraction

This reduces the probability of `413 Payload Too Large` errors while retaining
high-value information from the source content.

----------------------------------------------------------------------------------------------------------

## Anti-Bot Strategy

The crawler supports:

- async HTTP requests
- realistic request headers
- throttling
- retry/backoff
- Playwright fallback
- per-host concurrency controls
- graceful handling of blocked pages

For heavily protected sources, the architecture recommends browser-based
rendering only for high-value pages rather than using Playwright for every
request.

----------------------------------------------------------------------------------------------------------

## Freshness and Deduplication
News and job ingestion enforce a strict 24-hour freshness window.
Publication timestamps are normalized to UTC before validation.
Duplicate records are removed using stable source URLs and deterministic
normalization rules.
Entity resolution additionally canonicalizes variations such as:

OpenAI
Open AI
OpenAI, Inc.
        ↓
OpenAI


----------------------------------------------------------------------------------------------------------

## Engineering Principles
The project prioritizes:
- source traceability
- asynchronous ingestion
- deterministic validation
- graceful provider failure
- freshness guarantees
- deduplication
- evidence-backed extraction
- modularity
- scalability

-----------------------------------------------------------------------------------------------------------

# Output Structure
## Typical outputs include:
products.json
product_rejections.json
product_bulk_unresolved.json
product_bulk_stats.json

news.json
news_rejections.json

jobs.json
job_rejections.json

entity_mapping.json


## The final datasets can be exported into the required six logical spreadsheet
tabs:
Startups
Products
Research Papers
Jobs
News
Entity Mapping Log
----------------------------------------------------------------------------------------------------------
