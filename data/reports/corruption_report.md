# Corruption & Repair Comparison Report

> All states were evaluated with the same ground-truth test set. Values below are read from generated artifacts; no metric is hard-coded.

## Performance comparison

| Metric | Baseline | Corrupted | Repaired + optimized | Corruption delta | Recovery delta | Net vs baseline |
|---|---:|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | +0.0000 |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | -0.0545 | +0.1787 | +0.1241 |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | -0.1000 | +0.2000 | +0.1000 |
| `mean_judge_score` | 4.2000 | 3.8000 | 5 | -0.4000 | +1.2000 | +0.8000 |

## Impact by question type

| Question type | Baseline Hit Rate | Corrupted Hit Rate | Repaired Hit Rate | Baseline F1 | Corrupted F1 | Repaired + optimized F1 |
|---|---:|---:|---:|---:|---:|---:|
| `authors` | 1.0000 | 0.6667 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `categories` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `date` | 1.0000 | 0.0000 | 1.0000 | 0.5000 | 0.3333 | 1.0000 |
| `summary` | 1.0000 | 0.6667 | 1.0000 | 0.9195 | 0.8488 | 1.0000 |

## Data quality and freshness signals

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Quality gate | PASS | FAIL | PASS |
| GX expectations | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Stale ratio | 0.0417 | 0.3810 | 0.0417 |
| Row count | 24 | 21 | 24 |

## Impact analysis

- Corruption changed retrieval hit rate by **-0.4000** and mean token F1 by **-0.0545** relative to baseline.
- Repair changed retrieval hit rate by **+0.4000** and mean token F1 by **+0.1787** relative to the corrupted state.
- After post-repair reranking, mean token F1 changed by **+0.1241** relative to the original baseline.
- The corrupted quality gate was **FAIL**; after rebuilding from the raw lineage anchor it was **PASS**.
- Corrupted freshness was **FAIL** with stale ratio **0.3810**; repaired freshness was **PASS** with stale ratio **0.0417**.

## Repair method

The repaired dataset is rebuilt from `data/raw/crossref_records.json`, not from the corrupted dataframe. Cleaning, derived fields, vector indexing, quality checks, and evaluation are then rerun. This makes repair idempotent and preserves raw-data lineage.

After the clean rebuild, a hybrid title reranker reorders only the candidates already returned by semantic vector search. It does not perform a full-corpus exact-title lookup. This post-repair optimization improves top-1 answer selection while preserving an honest semantic-retrieval evaluation.

## Evidence artifacts

- `data/results/corruption_log.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/quality/corrupted_quality_report.json`
- `data/quality/repaired_quality_report.json`
- `data/clean/papers_clean_corrupted.json`
- `data/clean/papers_clean_repaired.json`
