from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import time

from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_ATTEMPTS = 3
JATS_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_jats_tags(abstract: str) -> str:
    return normalize_whitespace(JATS_TAG_RE.sub(" ", abstract))


def _format_date_parts(date_parts: list[list[int]] | None) -> str | None:
    if not date_parts or not date_parts[0]:
        return None
    parts = date_parts[0]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _format_authors(author_entries: list[dict]) -> list[str]:
    names = []
    for entry in author_entries or []:
        given = (entry.get("given") or "").strip()
        family = (entry.get("family") or "").strip()
        full_name = normalize_whitespace(f"{given} {family}")
        if full_name:
            names.append(full_name)
    return names


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = (item.get("DOI") or "").strip()
        title_list = item.get("title") or []
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not paper_id or not title:
            continue

        summary = _strip_jats_tags(item.get("abstract") or "")
        authors = _format_authors(item.get("author") or [])
        categories = [normalize_whitespace(c) for c in (item.get("subject") or []) if c]
        primary_category = categories[0] if categories else "Uncategorized"

        published = _format_date_parts(item.get("published", {}).get("date-parts"))
        if not published:
            created_dt = item.get("created", {}).get("date-time")
            published = created_dt.split("T")[0] if created_dt else ""

        created_dt = item.get("created", {}).get("date-time")
        updated = created_dt.split("T")[0] if created_dt else published

        url = item.get("URL") or f"https://doi.org/{paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {paper_id}",
            )
        )

    return records


def _records_to_json(records: list[PaperRecord]) -> list[dict]:
    return [asdict(record) for record in records]


def _request_crossref_payload(settings: Settings) -> dict | None:
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(CROSSREF_API_URL, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2**attempt)
            continue

        if response.status_code in RETRYABLE_STATUS_CODES:
            time.sleep(2**attempt)
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError:
            return None

        return response.json()

    return None


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records.

    Neu API loi (mat mang / 429 / 503) sau khi retry, fallback doc snapshot
    local `settings.paths.raw_api_response` roi cuoi cung la
    `settings.paths.raw_records_json` de dam bao pipeline khong bi chan.
    """
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    payload = _request_crossref_payload(settings)

    if payload is None and settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)

    if payload is not None:
        records = parse_crossref_payload(payload)
        if records:
            write_json(settings.paths.raw_api_response, payload)
            write_json(settings.paths.raw_records_json, _records_to_json(records))
            return records

    if settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    raise RuntimeError(
        "Unable to fetch Crossref records: no network response and no local fallback snapshot found."
    )


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    raw_items = read_json(path)
    return [PaperRecord(**item) for item in raw_items]
