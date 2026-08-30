"""
AI Intelligence Pipeline -> Google Sheets uploader

Creates/updates one spreadsheet with these 6 tabs:
1. Startups
2. Products
3. Research Papers
4. Jobs
5. News
6. Entity Mapping Log

The script reads JSON files from <project>/data.
It never invents missing research/startup records.

Setup:
    pip install gspread google-auth python-dotenv

Create a Google Cloud service account, download its JSON key, and save it as:
    credentials/google_service_account.json

Share the target Google Sheet with the service-account email, or let this script
create the spreadsheet and then share the resulting URL manually.

Environment variables:
    GOOGLE_SERVICE_ACCOUNT_FILE=credentials/google_service_account.json
    GOOGLE_SHEET_NAME=AI Intelligence Pipeline

Run:
    python -m src.integrations.google_sheets_uploader
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

CREDENTIALS_FILE = ROOT / os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "credentials/google_service_account.json",
)
SHEET_NAME = os.getenv(
    "GOOGLE_SHEET_NAME",
    "AI Intelligence Pipeline",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TAB_NAMES = [
    "Startups",
    "Products",
    "Research Papers",
    "Jobs",
    "News",
    "Entity Mapping Log",
]


def load_json(name: str) -> Any:
    path = DATA / name
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] Could not read {path}: {exc}")
        return []


def flatten(value: Any, prefix: str = "") -> dict[str, str]:
    """
    Flatten nested JSON into spreadsheet-friendly columns.
    Lists/dicts that cannot be meaningfully expanded are serialized as JSON.
    """
    result: dict[str, str] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, dict):
                result.update(flatten(child, name))
            elif isinstance(child, list):
                result[name] = json.dumps(child, ensure_ascii=False)
            else:
                result[name] = "" if child is None else str(child)
    else:
        result[prefix or "value"] = "" if value is None else str(value)

    return result


def records_from_json(data: Any) -> list[dict[str, str]]:
    if isinstance(data, list):
        output = []
        for item in data:
            if isinstance(item, dict):
                output.append(flatten(item))
        return output

    if isinstance(data, dict):
        # Common wrappers.
        for key in ("records", "data", "items", "results", "entities", "mappings"):
            if isinstance(data.get(key), list):
                return records_from_json(data[key])

        return [flatten(data)]

    return []


def records_from_products(data: Any) -> list[dict[str, str]]:
    """
    Product records use the canonical schema:
    source.*, content.*, _evidence.*, collectedAt, etc.
    """
    return records_from_json(data)


def records_from_entity_mapping(data: Any) -> list[dict[str, str]]:
    rows = records_from_json(data)

    # Keep mapping tab readable and put the most useful fields first when found.
    preferred = [
        "raw_name",
        "raw",
        "rawEntity",
        "canonical_name",
        "canonical",
        "canonicalEntity",
        "method",
        "resolution_method",
        "confidence",
        "status",
    ]

    normalized_rows = []
    for row in rows:
        ordered = {}
        for key in preferred:
            if key in row:
                ordered[key] = row[key]
        for key, value in row.items():
            if key not in ordered:
                ordered[key] = value
        normalized_rows.append(ordered)

    return normalized_rows


def derive_startups_from_products(products: Any) -> list[dict[str, str]]:
    """
    Only derives startup names that are explicitly present in product records.
    This is NOT a substitute for a dedicated startup crawler.
    """
    rows = []
    seen = set()

    if not isinstance(products, list):
        return rows

    for item in products:
        if not isinstance(item, dict):
            continue

        content = item.get("content")
        source = item.get("source")
        evidence = item.get("_evidence")

        if not isinstance(content, dict):
            content = {}
        if not isinstance(source, dict):
            source = {}
        if not isinstance(evidence, dict):
            evidence = {}

        name = (
            content.get("startupName")
            or item.get("startupName")
            or item.get("company")
        )
        if not name:
            continue

        key = str(name).strip().lower()
        if key in seen:
            continue
        seen.add(key)

        rows.append(
            {
                "startupName": str(name),
                "source": source.get("name", "Product Hunt"),
                "sourceUrl": source.get("url", ""),
                "productWebsite": evidence.get("productWebsite", ""),
                "collectedAt": item.get("collectedAt", ""),
            }
        )

    return rows


def prepare_rows(tab: str) -> list[dict[str, str]]:
    if tab == "Products":
        return records_from_products(load_json("products.json"))

    if tab == "Entity Mapping Log":
        return records_from_entity_mapping(load_json("entity_mapping.json"))

    if tab == "Jobs":
        # Current pipeline output.
        return records_from_json(load_json("jobs.json"))

    if tab == "News":
        return records_from_json(load_json("news.json"))

    if tab == "Research Papers":
        # Support a few sensible filenames without assuming one exists.
        for filename in (
            "research.json",
            "research_papers.json",
            "papers.json",
            "research_papers_output.json",
        ):
            data = load_json(filename)
            if data:
                return records_from_json(data)
        return []

    if tab == "Startups":
        # Prefer a dedicated startup output if the project has one.
        for filename in (
            "startups.json",
            "startup.json",
            "companies.json",
        ):
            data = load_json(filename)
            if data:
                return records_from_json(data)

        # Otherwise expose only startup names explicitly present in products.
        return derive_startups_from_products(load_json("products.json"))

    return []


def write_tab(spreadsheet, tab_name: str, rows: list[dict[str, str]]) -> None:
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=tab_name,
            rows=max(100, len(rows) + 10),
            cols=max(10, max((len(r) for r in rows), default=8)),
        )

    if not rows:
        worksheet.update(
            range_name="A1",
            values=[
                [tab_name],
                ["No source records available in the current data/ directory."],
            ],
        )
        worksheet.freeze(rows=1)
        return

    # Stable union of columns.
    headers: list[str] = []
    seen = set()

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                headers.append(key)

    values = [headers]
    for row in rows:
        values.append([row.get(h, "") for h in headers])

    worksheet.resize(
        rows=max(len(values) + 5, 100),
        cols=max(len(headers) + 2, 10),
    )
    worksheet.update(range_name="A1", values=values)

    worksheet.freeze(rows=1)

    # Basic formatting; no manual data entry required.
    worksheet.format(
        f"A1:{gspread.utils.rowcol_to_a1(1, len(headers))}",
        {
            "textFormat": {"bold": True},
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        },
    )


def main() -> None:
    print("=" * 70)
    print("AI INTELLIGENCE PIPELINE -> GOOGLE SHEETS")
    print("=" * 70)

    if not CREDENTIALS_FILE.exists():
        raise SystemExit(
            "\nGoogle credentials not found.\n"
            f"Expected: {CREDENTIALS_FILE}\n\n"
            "Create a Google Cloud service account, download its JSON key, "
            "and place it at that path."
        )

    credentials = Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
    )

    client = gspread.authorize(credentials)

    try:
        spreadsheet = client.open(SHEET_NAME)
        print(f"Updating existing spreadsheet: {SHEET_NAME}")
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SHEET_NAME)
        print(f"Created spreadsheet: {SHEET_NAME}")

    # Remove default Sheet1 only when we have successfully created the required tabs.
    for tab in TAB_NAMES:
        rows = prepare_rows(tab)
        write_tab(spreadsheet, tab, rows)
        print(f"{tab:22} : {len(rows)} records")

    try:
        default = spreadsheet.worksheet("Sheet1")
        if default.title not in TAB_NAMES:
            spreadsheet.del_worksheet(default)
    except gspread.WorksheetNotFound:
        pass

    print()
    print("Google Sheet ready.")
    print(f"URL: {spreadsheet.url}")


if __name__ == "__main__":
    main()
