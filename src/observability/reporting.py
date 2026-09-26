from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def _display(value: Any, digits: int = 4) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    if value is None:
        return "N/A"
    return str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the evidence report for the clean baseline pipeline."""
    by_type = metrics.get("by_question_type", {})
    type_rows = [
        "| Question type | Samples | Retrieval Hit Rate | Mean Token F1 |",
        "|---|---:|---:|---:|",
    ]
    for question_type, values in sorted(by_type.items()):
        type_rows.append(
            f"| `{question_type}` | {values.get('samples', 0)} | "
            f"{_display(values.get('retrieval_hit_rate'))} | "
            f"{_display(values.get('mean_token_f1'))} |"
        )

    expectations = quality.get("expectations", [])
    passed_expectations = sum(bool(item.get("success")) for item in expectations)
    ragas = metrics.get("ragas", {})
    ragas_status = ragas.get("skipped") or ragas.get("error") or "Completed"

    lines = [
        "# Phase 1 — Baseline Pipeline Report",
        "",
        "> This report is generated from pipeline artifacts. No metric is manually entered.",
        "",
        "## Source and index",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run time (UTC) | {_display(source_summary.get('run_at_utc'))} |",
        f"| Source | {_display(source_summary.get('source_api'))} |",
        f"| Raw records | {_display(source_summary.get('raw_records'))} |",
        f"| Clean records | {_display(source_summary.get('clean_records'))} |",
        f"| Indexed documents | {_display(source_summary.get('indexed_documents'))} |",
        f"| Chroma collection | `{_display(source_summary.get('collection_name'))}` |",
        f"| Embedding model | `{_display(source_summary.get('embedding_model'))}` |",
        f"| Evaluation questions | {_display(source_summary.get('evaluation_questions'))} |",
        f"| Agent provider | `{_display(source_summary.get('llm_provider'))}` |",
        f"| Agent model | `{_display(source_summary.get('llm_model'))}` |",
        "",
        "## Baseline evaluation",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Samples | {_display(metrics.get('samples'))} |",
        f"| Retrieval Hit Rate | {_display(metrics.get('retrieval_hit_rate'))} |",
        f"| Mean Token F1 | {_display(metrics.get('mean_token_f1'))} |",
        f"| Judge Accuracy | {_display(metrics.get('judge_accuracy'))} |",
        f"| Mean Judge Score | {_display(metrics.get('mean_judge_score'))} |",
        "",
        *type_rows,
        "",
        f"Ragas status: {ragas_status}",
        "",
        "## Data quality gate",
        "",
        f"- Overall quality: **{_display(quality.get('success'))}**",
        f"- Great Expectations: **{_display(quality.get('gx_success'))}**",
        f"- Validated rows: **{_display(quality.get('row_count'))}**",
        f"- Expectations passed: **{passed_expectations}/{len(expectations)}**",
        "",
        "## Freshness SLA",
        "",
        f"- Freshness status: **{_display(freshness.get('is_fresh'))}**",
        f"- Latest publication: `{_display(freshness.get('latest_published'))}`",
        f"- Oldest publication: `{_display(freshness.get('oldest_published'))}`",
        f"- Stale rows: **{_display(freshness.get('stale_rows'))}/{_display(freshness.get('total_rows'))}**",
        f"- Stale ratio: **{_display(freshness.get('stale_ratio'))}**",
        f"- SLA maximum ratio: **{_display(freshness.get('sla_ratio'))}**",
        f"- Stale threshold: **{_display(freshness.get('threshold_days'))} days**",
        "",
        "## Reproduce",
        "",
        "```powershell",
        f"$env:LLM_PROVIDER='{_display(source_summary.get('llm_provider'))}'",
        f"$env:LLM_MODEL='{_display(source_summary.get('llm_model'))}'",
        ".\\.venv\\Scripts\\python.exe script\\run_phase1.py",
        "```",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
) -> None:
    """Write an evidence-based comparison of all three pipeline states."""

    def display(value: Any) -> str:
        if isinstance(value, bool):
            return "PASS" if value else "FAIL"
        if isinstance(value, float):
            return f"{value:.4f}"
        if value is None:
            return "N/A"
        return str(value)

    def metric_delta(after: dict[str, Any], before: dict[str, Any], key: str) -> str:
        try:
            return f"{float(after[key]) - float(before[key]):+.4f}"
        except (KeyError, TypeError, ValueError):
            return "N/A"

    metric_names = [
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ]
    metric_rows = [
        "| Metric | Baseline | Corrupted | Repaired + optimized | Corruption delta | Recovery delta | Net vs baseline |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in metric_names:
        metric_rows.append(
            "| `{name}` | {baseline} | {corrupted} | {repaired} | {corruption_delta} | {repair_delta} | {net_delta} |".format(
                name=name,
                baseline=display(baseline_metrics.get(name)),
                corrupted=display(corrupted_metrics.get(name)),
                repaired=display(repaired_metrics.get(name)),
                corruption_delta=metric_delta(corrupted_metrics, baseline_metrics, name),
                repair_delta=metric_delta(repaired_metrics, corrupted_metrics, name),
                net_delta=metric_delta(repaired_metrics, baseline_metrics, name),
            )
        )

    baseline_by_type = baseline_metrics.get("by_question_type", {})
    corrupted_by_type = corrupted_metrics.get("by_question_type", {})
    repaired_by_type = repaired_metrics.get("by_question_type", {})
    question_types = sorted(
        set(baseline_by_type) | set(corrupted_by_type) | set(repaired_by_type)
    )
    question_type_rows = [
        "| Question type | Baseline Hit Rate | Corrupted Hit Rate | Repaired Hit Rate | Baseline F1 | Corrupted F1 | Repaired + optimized F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for question_type in question_types:
        baseline_values = baseline_by_type.get(question_type, {})
        corrupted_values = corrupted_by_type.get(question_type, {})
        repaired_values = repaired_by_type.get(question_type, {})
        question_type_rows.append(
            f"| `{question_type}` | "
            f"{display(baseline_values.get('retrieval_hit_rate'))} | "
            f"{display(corrupted_values.get('retrieval_hit_rate'))} | "
            f"{display(repaired_values.get('retrieval_hit_rate'))} | "
            f"{display(baseline_values.get('mean_token_f1'))} | "
            f"{display(corrupted_values.get('mean_token_f1'))} | "
            f"{display(repaired_values.get('mean_token_f1'))} |"
        )

    baseline_quality_value = (
        baseline_quality.get("success") if baseline_quality is not None else None
    )
    baseline_freshness_value = (
        baseline_quality.get("freshness", {}).get("is_fresh")
        if baseline_quality is not None
        else None
    )
    signal_rows = [
        "| Signal | Baseline | Corrupted | Repaired |",
        "|---|---:|---:|---:|",
        f"| Quality gate | {display(baseline_quality_value)} | {display(corrupted_quality.get('success'))} | {display(repaired_quality.get('success'))} |",
        f"| GX expectations | {display(baseline_quality.get('gx_success') if baseline_quality else None)} | {display(corrupted_quality.get('gx_success'))} | {display(repaired_quality.get('gx_success'))} |",
        f"| Freshness SLA | {display(baseline_freshness_value)} | {display(corrupted_freshness.get('is_fresh'))} | {display(repaired_freshness.get('is_fresh'))} |",
        f"| Stale ratio | {display((baseline_quality or {}).get('freshness', {}).get('stale_ratio'))} | {display(corrupted_freshness.get('stale_ratio'))} | {display(repaired_freshness.get('stale_ratio'))} |",
        f"| Row count | {display((baseline_quality or {}).get('row_count'))} | {display(corrupted_quality.get('row_count'))} | {display(repaired_quality.get('row_count'))} |",
    ]

    hit_drop = metric_delta(corrupted_metrics, baseline_metrics, "retrieval_hit_rate")
    hit_recovery = metric_delta(repaired_metrics, corrupted_metrics, "retrieval_hit_rate")
    f1_drop = metric_delta(corrupted_metrics, baseline_metrics, "mean_token_f1")
    f1_recovery = metric_delta(repaired_metrics, corrupted_metrics, "mean_token_f1")
    f1_net_gain = metric_delta(repaired_metrics, baseline_metrics, "mean_token_f1")
    report = "\n".join(
        [
            "# Corruption & Repair Comparison Report",
            "",
            "> All states were evaluated with the same ground-truth test set. Values below are read from generated artifacts; no metric is hard-coded.",
            "",
            "## Performance comparison",
            "",
            *metric_rows,
            "",
            "## Impact by question type",
            "",
            *question_type_rows,
            "",
            "## Data quality and freshness signals",
            "",
            *signal_rows,
            "",
            "## Impact analysis",
            "",
            f"- Corruption changed retrieval hit rate by **{hit_drop}** and mean token F1 by **{f1_drop}** relative to baseline.",
            f"- Repair changed retrieval hit rate by **{hit_recovery}** and mean token F1 by **{f1_recovery}** relative to the corrupted state.",
            f"- After post-repair reranking, mean token F1 changed by **{f1_net_gain}** relative to the original baseline.",
            f"- The corrupted quality gate was **{display(corrupted_quality.get('success'))}**; after rebuilding from the raw lineage anchor it was **{display(repaired_quality.get('success'))}**.",
            f"- Corrupted freshness was **{display(corrupted_freshness.get('is_fresh'))}** with stale ratio **{display(corrupted_freshness.get('stale_ratio'))}**; repaired freshness was **{display(repaired_freshness.get('is_fresh'))}** with stale ratio **{display(repaired_freshness.get('stale_ratio'))}**.",
            "",
            "## Repair method",
            "",
            "The repaired dataset is rebuilt from `data/raw/crossref_records.json`, not from the corrupted dataframe. Cleaning, derived fields, vector indexing, quality checks, and evaluation are then rerun. This makes repair idempotent and preserves raw-data lineage.",
            "",
            "After the clean rebuild, a hybrid title reranker reorders only the candidates already returned by semantic vector search. It does not perform a full-corpus exact-title lookup. This post-repair optimization improves top-1 answer selection while preserving an honest semantic-retrieval evaluation.",
            "",
            "## Evidence artifacts",
            "",
            "- `data/results/corruption_log.json`",
            "- `data/results/corrupted_metrics.json`",
            "- `data/results/repaired_metrics.json`",
            "- `data/quality/corrupted_quality_report.json`",
            "- `data/quality/repaired_quality_report.json`",
            "- `data/clean/papers_clean_corrupted.json`",
            "- `data/clean/papers_clean_repaired.json`",
            "",
        ]
    )
    write_text(Path(report_path), report)
