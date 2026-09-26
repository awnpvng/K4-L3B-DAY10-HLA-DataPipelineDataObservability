from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


FRESHNESS_SLA_RATIO = 0.25
REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "age_days",
    "text_for_embedding",
}


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = len(df)
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    valid_published = published.dropna()

    return {
        "latest_published": (
            valid_published.max().date().isoformat() if not valid_published.empty else None
        ),
        "oldest_published": (
            valid_published.min().date().isoformat() if not valid_published.empty else None
        ),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "sla_ratio": FRESHNESS_SLA_RATIO,
        "is_fresh": bool(total_rows and stale_ratio <= FRESHNESS_SLA_RATIO),
    }


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    normalized_name = safe_slug(report_name)
    if normalized_name == "baseline":
        return settings.paths.baseline_quality_report
    if normalized_name == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{normalized_name}_quality_report.json"


def _validate_schema(df: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Dataframe is missing required quality columns: {missing_columns}")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the GX 1.x quality gate and include the freshness SLA result."""
    _validate_schema(df)
    normalized_name = safe_slug(report_name)
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"{normalized_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{normalized_name}_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        name=f"{normalized_name}_batch"
    )
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=settings.max_results,
            max_value=settings.max_results,
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="title",
            min_value=8,
            max_value=500,
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="summary",
            min_value=40,
            max_value=10_000,
        ),
    ]
    validation_results = [batch.validate(expectation) for expectation in expectations]
    expectation_payloads = [result.to_json_dict() for result in validation_results]
    gx_success = all(result.success for result in validation_results)
    freshness = _freshness_payload(df, settings)

    report = {
        "success": bool(gx_success and freshness["is_fresh"]),
        "report_name": report_name,
        "row_count": len(df),
        "gx_success": bool(gx_success),
        "freshness": freshness,
        "expectations": expectation_payloads,
    }
    write_json(_quality_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a standalone freshness SLA report."""
    _validate_schema(df)
    report = _freshness_payload(df, settings)
    write_json(Path(report_path), report)
    return report
