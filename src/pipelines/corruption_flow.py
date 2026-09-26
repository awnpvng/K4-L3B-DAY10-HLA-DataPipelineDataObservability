from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe, repair_from_raw_snapshot
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_dataframe(path) -> pd.DataFrame:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON record list at {path}")
    return pd.DataFrame(payload)


def _require_artifacts(settings: Settings) -> None:
    required = [
        settings.paths.clean_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Run the Phase 1 pipeline before the corruption flow. Missing artifacts: "
            + ", ".join(missing)
        )


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _infer_baseline_run_date(clean_df: pd.DataFrame):
    """Recover the original cleaning date so repair reproduces baseline ages."""
    published = pd.to_datetime(clean_df["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(clean_df["age_days"], errors="coerce")
    candidates = (published + pd.to_timedelta(ages, unit="D")).dropna()
    if candidates.empty:
        raise ValueError("Cannot infer the baseline run date from published and age_days.")
    return candidates.mode().iloc[0].to_pydatetime()


def _print_comparison(
    baseline: dict[str, Any], corrupted: dict[str, Any], repaired: dict[str, Any]
) -> None:
    print("\nBaseline vs Corrupted vs Repaired")
    print(f"{'Metric':<24} {'Baseline':>12} {'Corrupted':>12} {'Repaired':>12}")
    print("-" * 63)
    for key in (
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ):
        values = [baseline.get(key), corrupted.get(key), repaired.get(key)]
        rendered = [f"{float(value):.4f}" if value is not None else "N/A" for value in values]
        print(f"{key:<24} {rendered[0]:>12} {rendered[1]:>12} {rendered[2]:>12}")


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Run corruption, automatic repair, re-evaluation, and comparison."""
    _require_artifacts(settings)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = _load_dataframe(settings.paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = corrupted_quality["freshness"]

    # Automated self-healing: a failed gate activates a rebuild from raw lineage.
    if corrupted_quality["success"]:
        raise RuntimeError(
            "Synthetic corruption did not trip the quality gate; refusing to claim a repair."
        )
    repaired_df = repair_from_raw_snapshot(
        settings, run_date=_infer_baseline_run_date(clean_df)
    )
    if set(repaired_df["paper_id"]) != set(clean_df["paper_id"]):
        raise RuntimeError("Repair document IDs do not match the baseline lineage.")
    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = repaired_quality["freshness"]

    baseline_quality = None
    if settings.paths.baseline_quality_report.exists():
        baseline_quality = read_json(settings.paths.baseline_quality_report)
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        baseline_quality=baseline_quality,
    )
    _print_comparison(
        baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary
    )
    print(f"\nComparison report: {settings.paths.comparison_report}")

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_bundle.summary,
        "repaired_metrics": repaired_bundle.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "repair_triggered": True,
        "comparison_report": str(settings.paths.comparison_report),
    }


def main() -> None:
    """CLI entry point for the corruption and repair pipeline."""
    run_corruption_flow_pipeline(load_settings())
