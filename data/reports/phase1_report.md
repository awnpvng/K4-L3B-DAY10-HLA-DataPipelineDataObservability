# Phase 1 — Baseline Pipeline Report

> This report is generated from pipeline artifacts. No metric is manually entered.

## Source and index

| Field | Value |
|---|---|
| Run time (UTC) | 2026-09-26T04:54:52.765828+00:00 |
| Source | Crossref REST API |
| Raw records | 24 |
| Clean records | 24 |
| Indexed documents | 24 |
| Chroma collection | `papers-baseline` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Evaluation questions | 10 |
| Agent provider | `mock` |
| Agent model | `mock` |

## Baseline evaluation

| Metric | Value |
|---|---:|
| Samples | 10 |
| Retrieval Hit Rate | 1.0000 |
| Mean Token F1 | 0.8759 |
| Judge Accuracy | 0.9000 |
| Mean Judge Score | 4.2000 |

| Question type | Samples | Retrieval Hit Rate | Mean Token F1 |
|---|---:|---:|---:|
| `authors` | 3 | 1.0000 | 1.0000 |
| `categories` | 2 | 1.0000 | 1.0000 |
| `date` | 2 | 1.0000 | 0.5000 |
| `summary` | 3 | 1.0000 | 0.9195 |

Ragas status: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## Data quality gate

- Overall quality: **PASS**
- Great Expectations: **PASS**
- Validated rows: **24**
- Expectations passed: **7/7**

## Freshness SLA

- Freshness status: **PASS**
- Latest publication: `2026-07-22`
- Oldest publication: `2026-03-28`
- Stale rows: **1/24**
- Stale ratio: **0.0417**
- SLA maximum ratio: **0.2500**
- Stale threshold: **180 days**

## Reproduce

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
.\.venv\Scripts\python.exe script\run_phase1.py
```
