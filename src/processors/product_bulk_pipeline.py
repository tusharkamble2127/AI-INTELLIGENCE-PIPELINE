from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path
import re
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
UNRESOLVED_FILE = DATA_DIR / "product_bulk_unresolved.json"
STATS_FILE = DATA_DIR / "product_bulk_stats.json"

TARGET_VALID = int(os.getenv("PRODUCT_VALID_TARGET", "1000"))
WEBSITE_CONCURRENCY = int(os.getenv("PRODUCT_WEBSITE_CONCURRENCY", "12"))
LLM_CONCURRENCY = int(os.getenv("PRODUCT_LLM_CONCURRENCY", "2"))
LLM_BATCH_SIZE = int(os.getenv("PRODUCT_LLM_BATCH_SIZE", "8"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

# Final run policy: do not waste quota/API calls on Product Hunt.
# This version is intentionally focused on recovering the existing unresolved queue.
USE_PRODUCT_HUNT = False

AI_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "ml", "llm",
    "generative ai", "genai", "gpt", "agent", "agents", "copilot",
    "automation", "computer vision", "nlp", "deep learning", "neural",
    "chatbot", "voice ai", "ai-powered", "ai powered",
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().strip().split())


def is_ai_product(product: dict[str, Any]) -> bool:
    text = " ".join(
        normalize(product.get(k))
        for k in ("name", "tagline", "description", "topics", "category")
    )
    return any(keyword in text for keyword in AI_KEYWORDS)


def canonical_key(product: dict[str, Any]) -> str:
    for key in ("id", "url", "website", "name", "product"):
        value = normalize(product.get(key))
        if value:
            return value
    return ""


def build_record(product: dict[str, Any], website: str | None = None) -> dict[str, Any]:
    name = (
        product.get("name")
        or product.get("product")
        or product.get("title")
        or "Unknown Product"
    )
    tagline = product.get("tagline") or product.get("description") or ""
    url = product.get("url") or product.get("product_url") or ""
    website = website or product.get("website")

    topics = product.get("topics", [])
    if isinstance(topics, list):
        topic_names = []
        for item in topics:
            if isinstance(item, dict):
                topic_names.append(item.get("name", ""))
            else:
                topic_names.append(str(item))
        topics = topic_names

    makers = product.get("makers", [])
    if isinstance(makers, list):
        maker_names = []
        for item in makers:
            if isinstance(item, dict):
                maker_names.append(item.get("name", ""))
            else:
                maker_names.append(str(item))
        makers = maker_names

    return {
        "id": product.get("id"),
        "name": name,
        "tagline": tagline,
        "url": url,
        "website": website,
        "createdAt": product.get("createdAt") or product.get("created_at"),
        "topics": topics,
        "makers": makers,
        "source": product.get("source", "Product Hunt"),
    }


async def fetch_website(
    session: aiohttp.ClientSession,
    product: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> tuple[dict[str, Any], str | None, str | None]:
    website = product.get("website")
    if website:
        return product, website, None

    url = product.get("url")
    if not url:
        return product, None, "WEBSITE_MISSING"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    async with semaphore:
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True,
            ) as response:
                if response.status >= 400:
                    return product, None, f"WEBSITE_HTTP_{response.status}"
                final_url = str(response.url)
                return product, final_url, None
        except Exception as exc:
            return product, None, f"WEBSITE_FETCH_FAILED: {type(exc).__name__}"


def deterministic_accept(product: dict[str, Any], website: str | None) -> bool:
    # Only accept records when there is enough evidence.
    # Website presence + AI-related metadata is sufficient for this recovery pass.
    if not website:
        return False
    return is_ai_product(product)


async def groq_classify_batch(
    session: aiohttp.ClientSession,
    batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not GROQ_API_KEY:
        return []

    prompt_items = []
    for idx, product in enumerate(batch):
        prompt_items.append(
            {
                "index": idx,
                "name": product.get("name") or product.get("product"),
                "tagline": product.get("tagline") or product.get("description"),
                "website": product.get("website"),
                "topics": product.get("topics"),
            }
        )

    system = (
        "You classify Product Hunt records for an AI product dataset. "
        "Return ONLY valid JSON: an array of objects with keys "
        "index, is_ai, confidence, reason. "
        "Use the supplied metadata only. Do not invent facts. "
        "is_ai must be true only when the product is clearly AI-related."
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(prompt_items, ensure_ascii=False),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=45),
        ) as response:
            if response.status >= 400:
                return []
            data = await response.json()
            content = data["choices"][0]["message"]["content"]
            match = re.search(r"\[.*\]", content, flags=re.S)
            if not match:
                return []
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


async def main() -> None:
    print("=" * 70)
    print("PRODUCT BULK PIPELINE - FINAL RECOVERY RUN")
    print("=" * 70)
    print(f"Valid target       : {TARGET_VALID}")
    print(f"Website concurrency: {WEBSITE_CONCURRENCY}")
    print(f"LLM concurrency    : {LLM_CONCURRENCY}")
    print(f"LLM primary        : Groq ({GROQ_MODEL})")
    print("Product Hunt       : DISABLED for final recovery run")
    print()

    products = load_json(PRODUCTS_FILE, [])
    if not isinstance(products, list):
        products = []

    unresolved = load_json(UNRESOLVED_FILE, [])
    if not isinstance(unresolved, list):
        unresolved = []

    print(f"Existing valid products: {len(products)}")
    print(f"Unresolved queue       : {len(unresolved)}")

    if not unresolved:
        print()
        print("No unresolved records available.")
        print("Nothing more can be recovered without collecting new candidates.")
        print("Existing products.json has been preserved.")
        return

    existing_keys = {canonical_key(p) for p in products if canonical_key(p)}
    queue = []
    seen_queue = set()

    for item in unresolved:
        if not isinstance(item, dict):
            continue

        # Old queue format stores the product name in "product".
        name = item.get("name") or item.get("product")
        if not name:
            continue

        candidate = dict(item)
        candidate["name"] = name

        key = canonical_key(candidate)
        if key and (key in existing_keys or key in seen_queue):
            continue

        seen_queue.add(key)
        queue.append(candidate)

    print(f"Retry candidates after deduplication: {len(queue)}")

    if not queue:
        print("All unresolved records are already present in products.json.")
        return

    connector = aiohttp.TCPConnector(limit=WEBSITE_CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=30)

    website_sem = asyncio.Semaphore(WEBSITE_CONCURRENCY)
    llm_sem = asyncio.Semaphore(LLM_CONCURRENCY)

    recovered: list[dict[str, Any]] = []
    still_unresolved: list[dict[str, Any]] = []

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print()
        print("Retrying website enrichment...")

        async def process_one(item: dict[str, Any]):
            product = build_record(item)
            original_name = product["name"]

            _, website, error = await fetch_website(
                session, product, website_sem
            )

            product["website"] = website

            if deterministic_accept(product, website):
                return product, None

            return None, {
                "product": original_name,
                "reason": error or "LLM_REQUIRED",
                "website": website,
                "_raw": product,
            }

        results = await asyncio.gather(
            *(process_one(item) for item in queue),
            return_exceptions=False,
        )

        llm_queue = []
        for valid, failed in results:
            if valid:
                recovered.append(valid)
            elif failed:
                llm_queue.append(failed)

        print(f"Deterministic recovered: {len(recovered)}")
        print(f"Remaining for Groq:     {len(llm_queue)}")

        # Groq is optional. If quota/key is exhausted, this step simply produces
        # no additional records and preserves the unresolved queue.
        if GROQ_API_KEY and llm_queue:
            print()
            print("Starting Groq recovery...")

            batches = [
                llm_queue[i:i + LLM_BATCH_SIZE]
                for i in range(0, len(llm_queue), LLM_BATCH_SIZE)
            ]

            async def run_batch(batch):
                async with llm_sem:
                    return await groq_classify_batch(
                        session,
                        [x["_raw"] for x in batch],
                    )

            for batch_no, (batch, decisions) in enumerate(
                zip(batches, await asyncio.gather(*(run_batch(b) for b in batches))),
                start=1,
            ):
                decision_map = {
                    int(d["index"]): d
                    for d in decisions
                    if isinstance(d, dict) and str(d.get("index", "")).isdigit()
                }

                for idx, item in enumerate(batch):
                    decision = decision_map.get(idx, {})
                    raw = item["_raw"]

                    if (
                        decision.get("is_ai") is True
                        and float(decision.get("confidence", 0) or 0) >= 0.70
                    ):
                        raw["llm_confidence"] = float(
                            decision.get("confidence", 0)
                        )
                        raw["llm_reason"] = decision.get("reason", "")
                        recovered.append(raw)
                    else:
                        still_unresolved.append(
                            {
                                "product": raw["name"],
                                "reason": "LLM_NOT_CONFIDENT",
                                "website": raw.get("website"),
                            }
                        )

                print(
                    f"Groq batch {batch_no}/{len(batches)} complete | "
                    f"recovered={len(recovered)}"
                )
        else:
            for item in llm_queue:
                raw = item["_raw"]
                still_unresolved.append(
                    {
                        "product": raw["name"],
                        "reason": item["reason"],
                        "website": raw.get("website"),
                    }
                )

    # Final deduplicated merge.
    added = 0
    for record in recovered:
        key = canonical_key(record)
        if not key or key in existing_keys:
            continue
        products.append(record)
        existing_keys.add(key)
        added += 1

    save_json(PRODUCTS_FILE, products)
    save_json(UNRESOLVED_FILE, still_unresolved)

    stats = {
        "target_valid": TARGET_VALID,
        "existing_before": len(products) - added,
        "recovered_this_run": added,
        "cumulative_products": len(products),
        "remaining_to_target": max(0, TARGET_VALID - len(products)),
        "unresolved_remaining": len(still_unresolved),
        "product_hunt_used": False,
        "groq_used": bool(GROQ_API_KEY and llm_queue),
    }
    save_json(STATS_FILE, stats)

    print()
    print("=" * 70)
    print("FINAL PRODUCT RECOVERY RESULT")
    print("=" * 70)
    print(f"Recovered this run : {added}")
    print(f"Cumulative products: {len(products)}")
    print(f"Remaining to 1000  : {max(0, TARGET_VALID - len(products))}")
    print(f"Still unresolved   : {len(still_unresolved)}")
    print()
    print(f"Products : {PRODUCTS_FILE.relative_to(ROOT)}")
    print(f"Queue    : {UNRESOLVED_FILE.relative_to(ROOT)}")
    print(f"Stats    : {STATS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
