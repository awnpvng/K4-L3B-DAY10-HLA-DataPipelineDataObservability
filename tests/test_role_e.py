from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import NOISE_TEXT, corrupt_clean_dataframe, repair_from_raw_snapshot
from ingestion.crossref import load_raw_records
from observability.reporting import generate_corruption_report
from pipelines.corruption_flow import _infer_baseline_run_date
from retrieval.index import SearchResult, TitleRerankedIndex


def _clean_dataframe(rows: int = 24) -> pd.DataFrame:
    published_start = datetime(2026, 6, 1, tzinfo=UTC)
    records = []
    for index in range(rows):
        published = (published_start + timedelta(days=index)).date().isoformat()
        title = f"A realistic scholarly paper title {index:02d}"
        summary = (
            f"This is a sufficiently detailed scholarly summary for record {index:02d}. "
            "It contains enough text for the quality gate."
        )
        records.append(
            {
                "paper_id": f"10.0000/paper-{index:02d}",
                "title": title,
                "summary": summary,
                "authors": [f"Author {index}"],
                "categories": ["RAG", "Evaluation"],
                "primary_category": "RAG",
                "published": published,
                "updated": published,
                "abs_url": f"https://doi.org/10.0000/paper-{index:02d}",
                "pdf_url": f"https://doi.org/10.0000/paper-{index:02d}",
                "comment": "fixture",
                "authors_joined": f"Author {index}",
                "categories_joined": "RAG, Evaluation",
                "summary_chars": len(summary),
                "age_days": 30,
                "text_for_embedding": "\n".join(
                    [
                        f"Title: {title}",
                        f"Authors: Author {index}",
                        f"Published: {published}",
                        "Categories: RAG, Evaluation",
                        f"Summary: {summary}",
                    ]
                ),
            }
        )
    return pd.DataFrame(records)


def test_corruption_suite_injects_all_six_scenarios_without_mutating_input(
    tmp_path,
) -> None:
    clean_df = _clean_dataframe()
    original = clean_df.copy(deep=True)
    log_path = tmp_path / "corruption_log.json"

    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    log = json.loads(log_path.read_text(encoding="utf-8"))

    pd.testing.assert_frame_equal(clean_df, original)
    assert len(corrupted) == 21
    assert log["input_rows"] == 24
    assert log["output_rows"] == 21
    assert log["scenario_count"] == 6
    assert [item["scenario"] for item in log["scenarios"]] == [
        "drop_latest_records",
        "blank_summary",
        "inject_noise",
        "truncate_title",
        "stale_date",
        "duplicate_rows",
    ]
    assert all(item["affected_count"] == len(item["changes"]) for item in log["scenarios"])
    assert (corrupted["summary"] == "").any()
    assert corrupted["summary"].str.contains(NOISE_TEXT, regex=False).any()
    assert (corrupted["title"].str.len() < 8).any()
    assert corrupted["paper_id"].duplicated().any()
    assert (corrupted["age_days"] > 180).mean() > 0.25
    assert all(
        f"Title: {row.title}" in row.text_for_embedding
        and f"Summary: {row.summary}" in row.text_for_embedding
        for row in corrupted.itertuples()
    )


def test_corruption_suite_rejects_invalid_input(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing required corruption columns"):
        corrupt_clean_dataframe(
            pd.DataFrame([{"paper_id": "incomplete"}]),
            tmp_path / "unused.json",
        )


def test_repair_from_raw_snapshot_is_idempotent() -> None:
    settings = load_settings()
    run_date = datetime(2026, 9, 26, tzinfo=UTC)
    expected = build_clean_dataframe(
        load_raw_records(settings.paths.raw_records_json), run_date
    )

    first = repair_from_raw_snapshot(settings, run_date=run_date)
    second = repair_from_raw_snapshot(settings, run_date=run_date)

    pd.testing.assert_frame_equal(first, expected)
    pd.testing.assert_frame_equal(second, expected)
    assert len(first) == settings.max_results == 24
    assert first["paper_id"].is_unique


def test_infer_baseline_run_date_reconstructs_original_day() -> None:
    clean_df = _clean_dataframe()
    expected = datetime(2026, 9, 26, tzinfo=UTC)
    published = pd.to_datetime(clean_df["published"], utc=True)
    clean_df["age_days"] = (pd.Timestamp(expected) - published).dt.days

    assert _infer_baseline_run_date(clean_df) == expected


def test_title_reranker_promotes_the_best_semantic_candidate_without_lookup() -> None:
    wrong = SearchResult(
        paper_id="paper-02",
        title="A Different Paper",
        score=0.95,
        content="wrong",
        metadata={},
    )
    expected = SearchResult(
        paper_id="paper-01",
        title="Target Paper",
        score=0.80,
        content="expected",
        metadata={},
    )

    class StubIndex:
        def search(self, query: str, top_k: int | None = None):
            return [wrong, expected]

        def lookup(self, value: str):
            raise AssertionError("Reranking must not use full-corpus exact lookup.")

    reranked = TitleRerankedIndex(StubIndex()).search(
        "When was the paper 'Target Paper' published?"
    )

    assert [item.paper_id for item in reranked] == ["paper-01", "paper-02"]


def test_corruption_report_uses_measured_metrics(tmp_path) -> None:
    report_path = tmp_path / "corruption_report.md"
    baseline = {
        "retrieval_hit_rate": 1.0,
        "mean_token_f1": 0.9,
        "judge_accuracy": 1.0,
        "mean_judge_score": 5.0,
        "by_question_type": {
            "summary": {
                "retrieval_hit_rate": 1.0,
                "mean_token_f1": 0.9,
            }
        },
    }
    corrupted = {
        "retrieval_hit_rate": 0.6,
        "mean_token_f1": 0.5,
        "judge_accuracy": 0.6,
        "mean_judge_score": 3.0,
        "by_question_type": {
            "summary": {
                "retrieval_hit_rate": 0.5,
                "mean_token_f1": 0.4,
            }
        },
    }
    repaired = {
        **baseline,
        "mean_token_f1": 1.0,
        "by_question_type": {
            "summary": {
                "retrieval_hit_rate": 1.0,
                "mean_token_f1": 1.0,
            }
        },
    }
    quality_fail = {"success": False, "gx_success": False, "row_count": 21}
    quality_pass = {"success": True, "gx_success": True, "row_count": 24}
    stale = {"is_fresh": False, "stale_ratio": 0.30}
    fresh = {"is_fresh": True, "stale_ratio": 0.04}

    generate_corruption_report(
        report_path,
        baseline,
        corrupted,
        repaired,
        quality_fail,
        quality_pass,
        stale,
        fresh,
        baseline_quality={
            **quality_pass,
            "freshness": fresh,
        },
    )

    report = report_path.read_text(encoding="utf-8")
    assert "| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000" in report
    assert "| `summary` | 1.0000 | 0.5000 | 1.0000" in report
    assert "Corruption changed retrieval hit rate by **-0.4000**" in report
    assert "mean token F1 changed by **+0.1000** relative to the original baseline" in report
    assert "| Quality gate | PASS | FAIL | PASS |" in report
