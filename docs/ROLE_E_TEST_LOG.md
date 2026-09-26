# Role E — Resilience Lead Test Log

Ngày kiểm tra: **2026-09-26**

## Phạm vi

- Synthetic corruption gồm 6 kịch bản.
- Corruption log có danh sách DOI và giá trị trước/sau.
- Quality Gate và Freshness SLA kích hoạt auto-repair.
- Repair idempotent từ `data/raw/crossref_records.json`.
- Đánh giá lại cùng một ground-truth test set.
- Báo cáo so sánh Baseline / Corrupted / Repaired.

## Lệnh kiểm tra

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
.\.venv\Scripts\python.exe script\run_corruption_flow.py
.\.venv\Scripts\python.exe -m pytest tests\test_role_e.py tests\test_role_d.py -q
```

## Kết quả kiểm thử

```text
18 passed in 36.67s
```

## Corruption scenarios

| Scenario | Số dòng bị tác động |
|---|---:|
| Drop latest records | 5 |
| Blank summary | 2 |
| Inject noise | 2 |
| Truncate title | 2 |
| Stale date | 6 |
| Duplicate rows | 2 |

Dataset thay đổi từ **24** thành **21** dòng sau khi drop và duplicate.

## Metrics thực tế

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval Hit Rate | 1.0000 | 0.6000 | 1.0000 |
| Mean Token F1 | 0.8759 | 0.8213 | 0.8759 |
| Judge Accuracy | 0.9000 | 0.8000 | 0.9000 |
| Mean Judge Score | 4.2000 | 3.8000 | 4.2000 |

## Observability signals

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Quality Gate | PASS | FAIL | PASS |
| Great Expectations | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Stale ratio | 0.0417 | 0.3810 | 0.0417 |
| Row count | 24 | 21 | 24 |

## Kết luận

Corruption làm Retrieval Hit Rate giảm **0.4**, khiến cả GX Quality Gate và Freshness SLA thất bại. Quality failure tự động kích hoạt rebuild từ raw lineage snapshot. Sau repair, toàn bộ metrics, row count, uniqueness và freshness trở về đúng giá trị baseline.

Artifact đối chiếu chính:

- `data/results/corruption_log.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/quality/corrupted_quality_report.json`
- `data/quality/repaired_quality_report.json`
- `data/reports/corruption_report.md`
