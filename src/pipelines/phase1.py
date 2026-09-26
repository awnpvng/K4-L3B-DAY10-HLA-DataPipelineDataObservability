from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings, normalized_provider
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def _make_embedding_manifest_portable(settings, index: LocalEmbeddingIndex) -> None:
    manifest = read_json(settings.paths.embeddings_json)
    manifest["persist_path"] = settings.paths.chroma_dir.resolve().relative_to(
        settings.paths.project_dir.resolve()
    ).as_posix()
    manifest["document_count"] = len(index.documents)
    write_json(settings.paths.embeddings_json, manifest)


def _run_agent_demo(settings, index: LocalEmbeddingIndex) -> list[dict[str, str]]:
    test_set = read_json(settings.paths.eval_testset)
    questions = [item["question"] for item in test_set[:3]]
    try:
        agent = build_agent(settings, index)
    except Exception as exc:
        return [{"question": question, "error": f"Agent initialization failed: {exc}"} for question in questions]

    demo_answers: list[dict[str, str]] = []
    for question in questions:
        try:
            demo_answers.append({"question": question, "answer": run_agent_question(agent, question)})
        except Exception as exc:
            demo_answers.append({"question": question, "error": f"Agent invocation failed: {exc}"})
    return demo_answers


def main() -> None:
    """Run the clean baseline from raw records through evaluation and reporting."""
    settings = load_settings()
    run_at = datetime.now(UTC)

    records = fetch_source_records(settings)
    clean_df = build_clean_dataframe(records, run_at)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced no records; baseline pipeline cannot continue.")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality gate; indexing was stopped.")

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    _make_embedding_manifest_portable(settings, index)
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    demo_answers = _run_agent_demo(settings, index)
    write_json(settings.paths.demo_answers, demo_answers)

    source_summary = {
        "run_at_utc": run_at.isoformat(),
        "source_api": settings.source_api,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "indexed_documents": index.collection.count(),
        "collection_name": index.collection_name,
        "embedding_model": settings.embedding_model,
        "evaluation_questions": len(test_set),
        "llm_provider": normalized_provider(settings),
        "llm_model": settings.model_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    print(
        "Phase 1 complete: "
        f"{len(clean_df)} clean records, "
        f"{index.collection.count()} indexed documents, "
        f"Hit Rate={evaluation.summary['retrieval_hit_rate']:.4f}, "
        f"Token F1={evaluation.summary['mean_token_f1']:.4f}"
    )
