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
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
