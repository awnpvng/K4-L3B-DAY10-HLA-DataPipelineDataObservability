from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


JATS_TAG_RE = re.compile(r"<[^>]+>")
CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def _clean_text(value: str | None) -> str:
    """Normalize whitespace and remove any remaining JATS/HTML tags."""
    return normalize_whitespace(unescape(JATS_TAG_RE.sub(" ", value or "")))


def _clean_string_list(values: list[str] | None) -> list[str]:
    """Normalize a string list while preserving order and removing duplicates."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = _clean_text(str(value))
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def _parse_date(value: str | None) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).normalize()


def _normalize_run_date(run_date: datetime) -> pd.Timestamp:
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    return run_timestamp.normalize()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw Crossref records into the stable pre-embedding schema.

    Invalid rows without an identifier, title, summary, or publication date are
    removed. Duplicate DOI values are resolved by keeping the most recently
    updated record. Dates remain ISO strings so they are safe Chroma metadata.
    """
    run_day = _normalize_run_date(run_date)
    rows: list[dict[str, object]] = []

    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published_date = _parse_date(record.published)

        if not paper_id or not title or not summary or published_date is None:
            continue

        updated_date = _parse_date(record.updated)
        if updated_date is None:
            updated_date = published_date
        authors = _clean_string_list(record.authors)
        categories = _clean_string_list(record.categories)
        authors_joined = ", ".join(authors) or "Unknown"
        categories_joined = ", ".join(categories) or "Uncategorized"
        primary_category = _clean_text(record.primary_category)
        if not primary_category:
            primary_category = categories[0] if categories else "Uncategorized"
        published = published_date.date().isoformat()
        updated = updated_date.date().isoformat()
        age_days = int((run_day - published_date).days)

        text_for_embedding = "\n".join(
            [
                f"Title: {title}",
                f"Authors: {authors_joined}",
                f"Published: {published}",
                f"Categories: {categories_joined}",
                f"Summary: {summary}",
            ]
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    dataframe = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    dataframe = (
        dataframe.sort_values(
            ["updated", "paper_id"], ascending=[False, True], kind="stable"
        )
        .drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
    return dataframe
