from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path

import pandas as pd

from core.config import Settings
from core.utils import normalize_whitespace, now_utc, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records


REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
    "age_days",
    "text_for_embedding",
}
NOISE_TEXT = "@@@### CORRUPTED_PAYLOAD xqzv_9999 !!! ???"


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Dataframe is missing required corruption columns: {missing}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")


def _rebuild_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep derived fields consistent with the intentionally corrupted source fields."""
    rebuilt = df.copy(deep=True)
    for column in ("published", "updated"):
        if column in rebuilt.columns:
            parsed_dates = pd.to_datetime(rebuilt[column], errors="coerce", utc=True)
            rebuilt[column] = parsed_dates.map(
                lambda value: value.date().isoformat() if not pd.isna(value) else ""
            )
    rebuilt["summary"] = rebuilt["summary"].fillna("").astype(str)
    rebuilt["summary_chars"] = rebuilt["summary"].str.len()
    rebuilt["text_for_embedding"] = rebuilt.apply(
        lambda row: "\n".join(
            [
                f"Title: {row['title']}",
                f"Authors: {row['authors_joined']}",
                f"Published: {row['published']}",
                f"Categories: {row['categories_joined']}",
                f"Summary: {row['summary']}",
            ]
        ),
        axis=1,
    )
    return rebuilt


def _event(
    name: str,
    row_ids: list[str],
    changes: list[dict[str, object]] | None = None,
    **details,
) -> dict[str, object]:
    return {
        "scenario": name,
        "affected_count": len(row_ids),
        "paper_ids": row_ids,
        "changes": changes or [],
        "details": details,
    }


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic production-like failures into a clean dataset.

    The function never mutates ``df``. Deterministic row selection makes the
    baseline/corrupted/repaired comparison reproducible during the live demo.
    """
    _validate_clean_dataframe(df)
    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict[str, object]] = []
    input_rows = len(corrupted)

    # 1. Simulate an incomplete incremental load by removing the newest 20%.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    latest_positions = (
        published.sort_values(ascending=False, na_position="last", kind="stable")
        .index[: max(1, math.ceil(input_rows * 0.20))]
        .tolist()
    )
    dropped_ids = corrupted.loc[latest_positions, "paper_id"].astype(str).tolist()
    dropped_changes = [
        {
            "paper_id": str(corrupted.loc[position, "paper_id"]),
            "before": {"published": str(corrupted.loc[position, "published"])},
            "after": None,
        }
        for position in latest_positions
    ]
    corrupted = corrupted.drop(index=latest_positions).reset_index(drop=True)
    events.append(
        _event(
            "drop_latest_records",
            dropped_ids,
            changes=dropped_changes,
            fraction=0.20,
        )
    )

    # Use disjoint, predictable rows for field-level corruptions where possible.
    affected_per_scenario = max(1, math.ceil(len(corrupted) * 0.10))
    positions = list(range(len(corrupted)))

    blank_positions = positions[:affected_per_scenario]
    blank_ids = corrupted.loc[blank_positions, "paper_id"].astype(str).tolist()
    blank_before = corrupted.loc[blank_positions, "summary"].astype(str).tolist()
    corrupted.loc[blank_positions, "summary"] = ""
    events.append(
        _event(
            "blank_summary",
            blank_ids,
            changes=[
                {"paper_id": paper_id, "before": before, "after": ""}
                for paper_id, before in zip(blank_ids, blank_before, strict=True)
            ],
            replacement="",
        )
    )

    noise_positions = positions[affected_per_scenario : 2 * affected_per_scenario]
    if not noise_positions:
        noise_positions = positions[:affected_per_scenario]
    noise_ids = corrupted.loc[noise_positions, "paper_id"].astype(str).tolist()
    noise_before = corrupted.loc[noise_positions, "summary"].astype(str).tolist()
    corrupted.loc[noise_positions, "summary"] = corrupted.loc[
        noise_positions, "summary"
    ].map(lambda value: normalize_whitespace(f"{NOISE_TEXT} {value}"))
    noise_after = corrupted.loc[noise_positions, "summary"].astype(str).tolist()
    events.append(
        _event(
            "inject_noise",
            noise_ids,
            changes=[
                {"paper_id": paper_id, "before": before, "after": after}
                for paper_id, before, after in zip(
                    noise_ids, noise_before, noise_after, strict=True
                )
            ],
            noise=NOISE_TEXT,
        )
    )

    title_positions = positions[2 * affected_per_scenario : 3 * affected_per_scenario]
    if not title_positions:
        title_positions = positions[-affected_per_scenario:]
    title_ids = corrupted.loc[title_positions, "paper_id"].astype(str).tolist()
    title_before = corrupted.loc[title_positions, "title"].astype(str).tolist()
    corrupted.loc[title_positions, "title"] = corrupted.loc[
        title_positions, "title"
    ].map(lambda value: (str(value)[:7] or "broken")[:7])
    title_after = corrupted.loc[title_positions, "title"].astype(str).tolist()
    events.append(
        _event(
            "truncate_title",
            title_ids,
            changes=[
                {"paper_id": paper_id, "before": before, "after": after}
                for paper_id, before, after in zip(
                    title_ids, title_before, title_after, strict=True
                )
            ],
            max_length=7,
        )
    )

    # Corrupt enough dates to cross the 25% freshness SLA after duplicates.
    stale_count = max(1, math.ceil(len(corrupted) * 0.30))
    stale_positions = positions[
        3 * affected_per_scenario : 3 * affected_per_scenario + stale_count
    ]
    if not stale_positions:
        stale_positions = positions[-stale_count:]
    stale_ids = corrupted.loc[stale_positions, "paper_id"].astype(str).tolist()
    stale_before = corrupted.loc[stale_positions, "published"].astype(str).tolist()
    stale_dates = pd.to_datetime(
        corrupted.loc[stale_positions, "published"], errors="coerce", utc=True
    ) - pd.Timedelta(days=365)
    corrupted.loc[stale_positions, "published"] = stale_dates.map(
        lambda value: value.date().isoformat() if not pd.isna(value) else "1900-01-01"
    )
    corrupted.loc[stale_positions, "age_days"] = (
        pd.to_numeric(corrupted.loc[stale_positions, "age_days"], errors="coerce")
        .fillna(0)
        .astype(int)
        + 365
    )
    stale_after = corrupted.loc[stale_positions, "published"].astype(str).tolist()
    events.append(
        _event(
            "stale_date",
            stale_ids,
            changes=[
                {"paper_id": paper_id, "before": before, "after": after}
                for paper_id, before, after in zip(
                    stale_ids, stale_before, stale_after, strict=True
                )
            ],
            days_shifted=365,
        )
    )

    # 6. Duplicate records last so paper_id uniqueness is observably violated.
    duplicate_count = max(1, math.ceil(len(corrupted) * 0.10))
    duplicate_rows = corrupted.iloc[-duplicate_count:].copy(deep=True)
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    events.append(
        _event(
            "duplicate_rows",
            duplicate_ids,
            changes=[
                {"paper_id": paper_id, "before": "one row", "after": "two rows"}
                for paper_id in duplicate_ids
            ],
            copies_per_row=1,
        )
    )

    corrupted = _rebuild_derived_columns(corrupted)
    log = {
        "version": 1,
        "deterministic": True,
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "scenario_count": len(events),
        "scenarios": events,
    }
    write_json(Path(output_log_path), log)
    return corrupted


def repair_from_raw_snapshot(
    settings: Settings, run_date: datetime | None = None
) -> pd.DataFrame:
    """Rebuild clean data from the immutable raw-record lineage anchor.

    Re-running this function is idempotent: it does not consume a corrupted
    artifact and therefore produces the same clean rows for the same snapshot
    and run date.
    """
    raw_path = settings.paths.raw_records_json
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw repair snapshot does not exist: {raw_path}")
    records = load_raw_records(raw_path)
    repaired = build_clean_dataframe(records, run_date or now_utc())
    if repaired.empty:
        raise RuntimeError("Repair produced no records from the raw snapshot.")
    return repaired
