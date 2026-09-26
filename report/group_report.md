# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | HLA |
| Repository | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trương Hoàng Thành An | 2A202602574 | A — Data Lead | `src/ingestion/crossref.py`, `data/raw/*` |
| 2 | Nguyễn Thị Bảo Trang | 2A202602580 | B — Quality Lead | `src/ingestion/cleaning.py`, `src/observability/quality.py` |
| 3 | Phan Thị Khánh Linh | 2A202602310 | C — Retrieval Lead | `src/retrieval/embeddings.py`, `src/retrieval/index.py` |
| 4 | Đàm Việt Hưng | 2A202602600 | D — Agent/Eval Lead | `src/retrieval/agent.py`, `llm.py`, `qa.py`, `src/evaluation/*` |
| 5 | Nguyễn Hồng Cường | 2A202602415 | E — Resilience Lead | `src/ingestion/corruption.py`, `script/run_corruption_flow.py`, `report/*` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ pipeline end-to-end từ ingestion đến corruption/repair. Baseline pipeline (`script/run_phase1.py`) tải 24 bài báo từ Crossref, làm sạch còn 24 dòng hợp lệ, index đủ 24 vector vào ChromaDB (`papers-baseline`), sinh 10 câu hỏi test qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`), và đạt Retrieval Hit Rate 1.0000, Mean Token F1 0.8759, Judge Accuracy 0.9000 trên agent provider `mock`. Great Expectations 1.x pass 7/7 expectation, Freshness SLA PASS (stale ratio 4.17% so với ngưỡng 25%).

Corruption suite tiêm đủ 6 kịch bản (drop latest records, blank summary, inject noise, truncate title, stale date, duplicate rows), làm số dòng hợp lệ giảm còn 21/24, khiến Quality Gate và Freshness SLA đều FAIL (stale ratio tăng lên 38.10%), Retrieval Hit Rate rơi từ 1.0000 xuống 0.6000 — corruption ảnh hưởng rõ nhất là `drop_latest_records` (mất 5 bản ghi mới nhất) và `stale_date` (6 bản ghi bị lùi ngày), khiến câu hỏi loại `date` sập Hit Rate về 0.0000.

Repair rebuild lại toàn bộ pipeline từ `data/raw/crossref_records.json` (raw lineage anchor), không sửa trực tiếp dữ liệu bẩn. Sau repair, Quality Gate và Freshness SLA quay lại PASS, Retrieval Hit Rate phục hồi về 1.0000, Mean Token F1 đạt 1.0000 (cao hơn cả baseline nhờ có thêm bước hybrid title reranker ở giai đoạn hậu-repair).

Giới hạn còn lại: Ragas evaluation chưa chạy (`RUN_RAGAS=0` mặc định) nên chưa có bộ metric Ragas độc lập để đối chiếu; agent demo hiện dùng provider `mock` thay vì LLM thật khi sinh báo cáo tự động.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (data/raw/)
    -> cleaning và data modeling (age_days, text_for_embedding)
    -> embedding (all-MiniLM-L6-v2) + ChromaDB index
    -> evaluation baseline (10 câu hỏi, 4 loại)
    -> quality/freshness reports (Great Expectations 1.x)
    -> corruption (6 kịch bản làm bẩn)
    -> re-index và re-evaluate trên dữ liệu bẩn
    -> repair từ raw snapshot (rebuild toàn bộ pipeline)
    -> comparison report (baseline vs corrupted vs repaired)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref REST API | Fetch có retry (429/503), parse JATS abstract, chuẩn hóa date/authors, fallback offline | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Trương Hoàng Thành An (A) |
| Cleaning | `PaperRecord` (24 bản ghi) | Khử trùng lặp theo `paper_id`, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv` / `.json` | Nguyễn Thị Bảo Trang (B) |
| Observability | Clean dataframe | GX 1.x ephemeral context, 4 expectations, Freshness SLA (ngưỡng 180 ngày / 25%) | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Nguyễn Thị Bảo Trang (B) |
| Embedding/index | Clean dataframe | Sinh vector `all-MiniLM-L6-v2`, nạp ChromaDB collection `papers-baseline` | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Phan Thị Khánh Linh (C) |
| Evaluation | Clean dataframe | Sinh 10 câu hỏi test (4 loại), đo Hit Rate & Token F1 | `data/eval/test_set.json`, `data/results/baseline_metrics.json` | Đàm Việt Hưng (D) |
| Agent | Vector index + câu hỏi | Router multi-provider (`mock`/`google`/`openai`/`anthropic`), trích xuất câu trả lời | `data/results/baseline_answers.json` | Đàm Việt Hưng (D) |
| Corruption/repair | Clean dataframe + raw records | 6 kịch bản làm bẩn, đo suy giảm, rebuild từ raw snapshot | `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` | Nguyễn Hồng Cường (E) |
| Orchestration | Toàn bộ module trên | Điều phối thứ tự chạy qua `script/run_phase1.py` và `script/run_corruption_flow.py` | `data/reports/phase1_report.md`, `corruption_report.md` | Cả nhóm |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `mock` (dùng khi sinh báo cáo để kết quả tái lập ổn định) |
| `LLM_MODEL` | `mock` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày, SLA tối đa 25% stale |
| Random seed | Không dùng (corruption suite deterministic theo `paper_id`, không random) |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-09-26T04:54:52Z | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption flow | Thành công | Cùng phiên chạy baseline | `data/reports/corruption_report.md`, `data/results/corrupted_metrics.json`, `repaired_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query.bibliographic=agentic retrieval augmented generation large language model`, `filter=from-pub-date:...,has-abstract:true` |
| Thời điểm lấy dữ liệu | Snapshot cố định tại `data/raw/crossref_response.json` (24 items) |
| Số record nhận được | 24/24 |
| Cơ chế retry/backoff | Retry tối đa 3 lần với backoff `2**attempt` giây khi gặp HTTP 429/503 hoặc lỗi mạng; fallback đọc lại `raw_api_response` hoặc `raw_records_json` cục bộ nếu API không khả dụng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string (DOI) | Có | Khóa định danh duy nhất | Bỏ record nếu rỗng |
| `title` | string | Có | Tiêu đề bài báo | Bỏ record nếu rỗng |
| `summary` | string | Không | Abstract đã bóc tag JATS | Ghi chuỗi rỗng nếu thiếu |
| `authors` | list[string] | Không | Danh sách tác giả `given family` | Bỏ tác giả thiếu cả given và family |
| `categories` / `primary_category` | list[string] / string | Không | Chủ đề Crossref `subject` | Gán `"Uncategorized"` nếu rỗng |
| `published` / `updated` | string ISO date | Có | Ngày xuất bản/tạo | Fallback từ `created.date-time` nếu thiếu `published` |
| `age_days` | int | Có (sau cleaning) | `run_date - published` (ngày) | Tính bởi B trong `cleaning.py` |
| `text_for_embedding` | string | Có (sau cleaning) | Ghép 5 phần: title, authors, categories, summary, published | Tính bởi B trong `cleaning.py` |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | --- | --- |
| Khử trùng lặp theo `paper_id` | Uniqueness | 0/24 (dữ liệu Crossref gốc không trùng) | `expect_column_values_to_be_unique` PASS trong `baseline_quality_report.json` |
| Tính `age_days` từ `published` | Timeliness | 24/24 | `freshness_report.json` |
| Ghép `text_for_embedding` đủ 5 phần | Completeness | 24/24 | `data/clean/papers_clean.json` |

`text_for_embedding` được B ghép từ 5 phần cấu trúc (title, authors, categories, summary, published) để cung cấp ngữ cảnh đầy đủ cho bước embedding; `age_days` tính bằng `(run_date - published).days` dùng cho Freshness SLA; document ID dùng trực tiếp DOI (`paper_id`) để đảm bảo nhất quán giữa raw, clean và vector index.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| Các `question_type` | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID | `ground_truth_doc_ids` gắn trực tiếp với DOI của bài báo nguồn khi sinh câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB local persist, collection `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `mock` khi sinh báo cáo tái lập; hỗ trợ `google`/`openai`/`anthropic` khi có API key |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (10 câu hỏi cố định, không sinh lại giữa 3 lần chạy) |

Test set được giữ nguyên (`refresh_test_set=False` mặc định) khi đánh giá baseline, corrupted và repaired để đảm bảo mọi chênh lệch về Hit Rate/F1 phản ánh đúng ảnh hưởng của corruption/repair lên dữ liệu, chứ không lẫn với nhiễu do câu hỏi khác nhau giữa các lần chạy.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 items, 2 file (response + records) |
| Cleaned dataset | `data/clean/` | Có | `papers_clean.csv` + `.json`, 24 dòng |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | 24 vector, collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi, 4 loại |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit Rate 1.0000, F1 0.8759 |
| Quality/freshness | `data/quality/` | Có | GX PASS 7/7, Freshness PASS |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh tự động từ artifact |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | --: | --- |
| `retrieval_hit_rate` | 1.0000 | Toàn bộ 10 câu hỏi retrieve đúng document ground-truth |
| `mean_token_f1` | 0.8759 | Câu trả lời khớp cao với ground truth, loại `date` thấp nhất (0.5000) do câu trả lời ngắn/định dạng ngày khác |
| `judge_accuracy` | 0.9000 | 9/10 câu được LLM-judge đánh giá đúng |
| `mean_judge_score` | 4.2000 | Điểm judge trung bình trên thang 5 |
| Ragas | N/A | `RUN_RAGAS=0` mặc định để giữ pipeline chạy nhanh trong buổi lab |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `expect_table_row_count_to_be_between` | Completeness | 24–24 dòng | PASS (24) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (paper_id, title, summary) | Completeness | 0% null | PASS | `baseline_quality_report.json` |
| `expect_column_values_to_be_unique` (paper_id) | Uniqueness | 100% unique | PASS | `baseline_quality_report.json` |
| `expect_column_value_lengths_to_be_between` (title, summary) | Validity | Độ dài hợp lệ | PASS | `baseline_quality_report.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | `data/clean/papers_clean.json` (baseline) |
| Timestamp mới nhất | `2026-07-22` |
| Ngưỡng freshness | 180 ngày / SLA tối đa 25% stale |
| Trạng thái baseline | Fresh (stale ratio 4.17%, 1/24 dòng) |
| Lý do | Chỉ 1/24 bài báo có `age_days > 180`, thấp hơn nhiều so với ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | --: | --- | --- | --- |
| `drop_latest_records` | Xóa 20% bản ghi có `published` mới nhất | 5 | Row count giảm dưới ngưỡng | Row count 24→21, `expect_table_row_count_to_be_between` FAIL | Rebuild từ raw snapshot đầy đủ 24 bản ghi |
| `blank_summary` | Xóa rỗng `summary` | 2 | Vi phạm not-null/length | Giảm chất lượng context cho agent | Lấy lại `summary` gốc từ raw |
| `inject_noise` | Chèn chuỗi rác vào `summary` | 2 | Vi phạm length/validity | Giảm Token F1 do context nhiễu | Rebuild `text_for_embedding` từ raw |
| `truncate_title` | Cắt `title` còn tối đa 7 ký tự | 2 | Vi phạm length tối thiểu title | Retrieval nhầm do title không đủ nghĩa | Khôi phục `title` đầy đủ từ raw |
| `stale_date` | Lùi `published` 365 ngày | 6 | Freshness SLA vi phạm | Stale ratio tăng 4.17%→38.10%, Freshness FAIL | Khôi phục `published` gốc, tính lại `age_days` |
| `duplicate_rows` | Nhân bản 1 bản sao mỗi dòng bị chọn | 2 | Vi phạm uniqueness | Tăng nhiễu retrieval | Khử trùng lặp lại theo `paper_id` khi rebuild |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 scenario, mỗi scenario có `affected_count`, `paper_ids` bị tác động và `details` tham số cụ thể (ví dụ `fraction: 0.2`, `days_shifted: 365`), đủ để truy vết chính xác bản ghi nào bị sửa.

Repair không sửa trực tiếp từng dòng dữ liệu bẩn mà rebuild toàn bộ pipeline (cleaning → embedding → index → quality → evaluation) từ `data/raw/crossref_records.json` — nguồn "lineage anchor" đáng tin cậy được A bảo toàn không đổi trong suốt buổi lab. Điều này đảm bảo tính idempotent: chạy repair nhiều lần luôn cho cùng một kết quả, thay vì áp các bản vá cục bộ có thể che giấu lỗi thay vì khắc phục gốc rễ.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | --: | --: | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | Phục hồi hoàn toàn về baseline |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | -0.0545 | +0.1787 | Vượt baseline nhờ hybrid reranker hậu-repair |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | -0.1000 | +0.2000 | Vượt baseline |
| `mean_judge_score` | 4.2000 | 3.8000 | 5.0000 | -0.4000 | +1.2000 | Vượt baseline |
| Quality checks pass/fail | PASS | FAIL | PASS | 7/7→FAIL | FAIL→PASS | Row count là nguyên nhân chính gây FAIL |
| Freshness status | PASS (4.17%) | FAIL (38.10%) | PASS (4.17%) | +33.93 điểm % stale | Về đúng baseline | `stale_date` là nguyên nhân chính |

1. `drop_latest_records` + `stale_date` (11/21 bản ghi bị ảnh hưởng) → Freshness SLA chuyển PASS→FAIL (stale ratio 4.17%→38.10%) → Retrieval Hit Rate giảm 1.0000→0.6000, rõ nhất ở câu hỏi loại `date` (Hit Rate 1.0000→0.0000).
2. Repair rebuild từ `crossref_records.json` → Quality Gate và Freshness SLA quay lại PASS (stale ratio về 4.17%) → toàn bộ metric agent (Hit Rate, F1, Judge Accuracy) phục hồi về hoặc vượt baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy thử `fetch_source_records()` với `REFRESH_SOURCE=1` để kiểm tra cơ chế gọi API thật, 2 file raw fixture chuẩn (`crossref_response.json`, `crossref_records.json`) bị ghi đè bằng dữ liệu Crossref live khác hoàn toàn nội dung/DOI so với fixture 24 bài báo dùng để chấm điểm.
- **Nguyên nhân:** `fetch_source_records` mặc định ưu tiên gọi API khi `refresh_source=True`, và Crossref API trả về kết quả khác nhau theo thời điểm truy vấn (không deterministic).
- **Cách xử lý:** Revert 2 file về bản gốc bằng `git checkout -- data/raw/crossref_records.json data/raw/crossref_response.json`; thống nhất giữ `REFRESH_SOURCE` không set (mặc định `false`) trong `.env` khi chạy demo/nộp bài.
- **Cách xác minh:** `git status --short data/raw/` không còn thay đổi; chạy lại `python script/run_phase1.py` vẫn ra đúng 24 bài báo và metrics baseline không đổi.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Ragas evaluation chưa bật (`RUN_RAGAS=0`) | Thiếu bộ metric Ragas độc lập để đối chiếu chéo với Token F1/Judge | Bật `RUN_RAGAS=1` trong CI, so sánh Ragas faithfulness/answer_relevancy với `mean_judge_score` hiện tại |
| Agent demo dùng provider `mock` khi sinh báo cáo | Chưa chứng minh chất lượng câu trả lời với LLM thật trong báo cáo tự động | Chạy lại `run_phase1.py`/`run_corruption_flow.py` với `LLM_PROVIDER=gemini` và đính kèm `agent_demo_answers.json` tương ứng vào report |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
