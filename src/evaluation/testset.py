from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


QUESTION_TYPE_COUNTS = {
    "summary": 3,
    "authors": 3,
    "date": 2,
    "categories": 2,
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return normalize_whitespace(", ".join(str(item) for item in value if str(item).strip()))
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return normalize_whitespace(str(value))


def _metadata_text(row: pd.Series, joined_column: str, source_column: str) -> str:
    joined = _text(row.get(joined_column))
    return joined or _text(row.get(source_column))


def _quote_title(title: str) -> str:
    quote = '"' if "'" in title else "'"
    return f"{quote}{title}{quote}"


def _question_and_answer(question_type: str, row: pd.Series) -> tuple[str, str]:
    title = _text(row["title"])
    quoted_title = _quote_title(title)
    if question_type == "summary":
        return f"Summarize the paper {quoted_title}.", first_sentence(_text(row.get("summary")))
    if question_type == "authors":
        return f"Who authored the paper {quoted_title}?", _metadata_text(row, "authors_joined", "authors")
    if question_type == "date":
        return f"When was the paper {quoted_title} published?", _text(row.get("published"))
    if question_type == "categories":
        return f"What categories are assigned to the paper {quoted_title}?", _metadata_text(
            row, "categories_joined", "categories"
        )
    raise ValueError(f"Unsupported question type: {question_type}")


def _has_answer(question_type: str, row: pd.Series) -> bool:
    _, answer = _question_and_answer(question_type, row)
    return bool(answer)


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Build a deterministic 10-question benchmark from cleaned paper data."""
    required_columns = {"paper_id", "title", "summary", "published"}
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing)}")

    papers = df.copy()
    papers["paper_id"] = papers["paper_id"].map(_text)
    papers["title"] = papers["title"].map(_text)
    papers = papers[(papers["paper_id"] != "") & (papers["title"] != "")]
    papers = papers.drop_duplicates(subset="paper_id", keep="first").sort_values(
        ["paper_id", "title"], kind="stable"
    )
    if papers.empty:
        raise ValueError("Clean dataframe contains no usable papers.")

    test_set: list[dict[str, Any]] = []
    used_doc_ids: set[str] = set()
    counters: Counter[str] = Counter()

    for question_type, count in QUESTION_TYPE_COUNTS.items():
        candidates = [row for _, row in papers.iterrows() if _has_answer(question_type, row)]
        if not candidates:
            raise ValueError(f"Cannot build {question_type} questions: no paper has a usable answer.")

        for _ in range(count):
            row = next(
                (candidate for candidate in candidates if _text(candidate["paper_id"]) not in used_doc_ids),
                candidates[counters[question_type] % len(candidates)],
            )
            counters[question_type] += 1
            paper_id = _text(row["paper_id"])
            used_doc_ids.add(paper_id)
            question, ground_truth = _question_and_answer(question_type, row)
            test_set.append(
                {
                    "id": f"{question_type}-{counters[question_type]:02d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(Path(output_path), test_set)
    return test_set
