from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from core.config import load_settings, normalized_provider
from evaluation.metrics import _token_f1, evaluate_pipeline
from evaluation.testset import QUESTION_TYPE_COUNTS, build_test_set
from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe
from ingestion.crossref import load_raw_records
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import SearchResult
from retrieval.qa import _extract_answer


def _clean_dataframe(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": f"paper-{index:02d}",
                "title": f"Paper {index}",
                "summary": f"Summary sentence {index}. More detail follows.",
                "authors_joined": f"Author {index}, Coauthor {index}",
                "categories_joined": "RAG, Evaluation",
                "published": f"2026-06-{index + 1:02d}",
            }
            for index in range(rows)
        ]
    )


def test_build_test_set_creates_ten_questions_across_four_types() -> None:
    output_path = Path(__file__).with_name(".generated_test_set.json")
    try:
        test_set = build_test_set(_clean_dataframe(), output_path)

        assert len(test_set) == 10
        assert {item["question_type"] for item in test_set} == set(QUESTION_TYPE_COUNTS)
        assert all(item["ground_truth"] for item in test_set)
        assert all(len(item["ground_truth_doc_ids"]) == 1 for item in test_set)
        assert json.loads(output_path.read_text(encoding="utf-8")) == test_set
    finally:
        output_path.unlink(missing_ok=True)


def test_build_test_set_validates_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_test_set(pd.DataFrame([{"paper_id": "one"}]), Path("unused.json"))


def test_role_b_clean_dataframe_builds_role_d_testset() -> None:
    settings = load_settings()
    records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(records, datetime.now(UTC))
    output_path = Path(__file__).with_name(".role_b_test_set.json")

    try:
        test_set = build_test_set(clean_df, output_path)

        assert clean_df.columns.tolist() == CLEAN_COLUMNS
        assert len(clean_df) == settings.max_results == 24
        assert clean_df["paper_id"].is_unique
        role_d_columns = ["authors_joined", "categories_joined", "text_for_embedding"]
        assert clean_df[role_d_columns].notna().all().all()
        assert len(test_set) == sum(QUESTION_TYPE_COUNTS.values()) == 10
    finally:
        output_path.unlink(missing_ok=True)


def test_token_f1_handles_punctuation_and_duplicate_tokens() -> None:
    assert _token_f1("RAG, RAG quality", "rag quality") == pytest.approx(0.8)
    assert _token_f1("no overlap", "different answer") == 0.0


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Who authored this paper?", "Ada, Grace"),
        ("When was this paper published?", "2026-06-01"),
        ("What categories are assigned?", "RAG, Evaluation"),
        ("Summarize this paper.", "First sentence."),
    ],
)
def test_extract_answer_for_each_question_type(question: str, expected: str) -> None:
    result = SearchResult(
        paper_id="paper-01",
        title="Paper 1",
        score=1.0,
        content="content",
        metadata={
            "authors_joined": "Ada, Grace",
            "published": "2026-06-01",
            "categories_joined": "RAG, Evaluation",
            "summary": "First sentence. Second sentence.",
        },
    )

    assert _extract_answer(question, result) == expected


def test_mock_agent_answers_from_local_index() -> None:
    search_result = SearchResult(
        paper_id="paper-01",
        title="Paper 1",
        score=1.0,
        content="content",
        metadata={"summary": "Grounded answer. More detail."},
    )

    class StubIndex:
        def lookup(self, value: str):
            return None

        def search(self, query: str, top_k: int | None = None):
            return [search_result]

    settings = replace(load_settings(), llm_provider="mock", model_name="mock")
    agent = build_agent(settings, StubIndex())

    assert run_agent_question(agent, "Summarize the best matching paper.") == "Grounded answer."


def test_google_provider_alias_maps_to_gemini() -> None:
    settings = replace(load_settings(), llm_provider="google")
    assert normalized_provider(settings) == "gemini"


def test_evaluate_pipeline_writes_hit_rate_and_token_f1() -> None:
    directory = Path(__file__).parent
    test_set_path = directory / ".evaluation_input.json"
    metrics_path = directory / ".evaluation_metrics.json"
    answers_path = directory / ".evaluation_answers.json"
    paths = (test_set_path, metrics_path, answers_path)
    test_set = [
        {
            "id": "summary-01",
            "question_type": "summary",
            "question": "Summarize Paper 1.",
            "ground_truth": "Grounded answer.",
            "ground_truth_doc_ids": ["paper-01"],
        }
    ]
    search_result = SearchResult(
        paper_id="paper-01",
        title="Paper 1",
        score=1.0,
        content="content",
        metadata={"summary": "Grounded answer. More detail."},
    )

    class StubIndex:
        def lookup(self, value: str):
            return None

        def search(self, query: str, top_k: int | None = None):
            return [search_result]

    try:
        test_set_path.write_text(json.dumps(test_set), encoding="utf-8")
        settings = replace(load_settings(), llm_provider="mock", model_name="mock")
        bundle = evaluate_pipeline(settings, StubIndex(), test_set_path, metrics_path, answers_path)

        assert bundle.summary["retrieval_hit_rate"] == 1.0
        assert bundle.summary["mean_token_f1"] == 1.0
        assert metrics_path.exists()
        assert answers_path.exists()
    finally:
        for path in paths:
            path.unlink(missing_ok=True)
