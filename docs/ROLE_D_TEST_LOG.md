# Role D Test Log — Agent & Evaluation

## 1. Phạm vi kiểm thử

- Vai trò: **D — Agent/Eval Lead**.
- Module kiểm thử:
  - `src/evaluation/testset.py`
  - `src/evaluation/metrics.py`
  - `src/retrieval/agent.py`
  - `src/retrieval/qa.py`
  - `src/pipelines/phase1.py`
  - `src/observability/reporting.py` (baseline report)
- File test: `tests/test_role_d.py`.
- Ngày kiểm thử: **26/09/2026**.

Role D không chỉnh sửa hoặc tiêm lỗi trực tiếp vào dữ liệu sạch của Role B. Các dữ liệu synthetic chỉ được tạo cô lập trong bộ nhớ hoặc trong file tạm và được xóa sau khi test kết thúc.

## 2. Dữ liệu đầu vào

### Dữ liệu thật dùng cho integration test

- `data/raw/crossref_records.json`: 24 bản ghi raw của Role A.
- `data/clean/papers_clean.json`: 24 bản ghi sạch của Role B.
- Schema Role B được Role D sử dụng:
  - `paper_id`
  - `title`
  - `summary`
  - `authors_joined`
  - `categories_joined`
  - `published`
  - `text_for_embedding`

### Dữ liệu synthetic dùng trong unit test

- DataFrame 12 paper mẫu để kiểm tra bộ sinh 10 câu hỏi.
- Một DataFrame chỉ có `paper_id` để kiểm tra lỗi thiếu schema.
- Một `SearchResult` giả lập để kiểm tra bốn dạng câu hỏi và mock agent.
- Một evaluation sample để kiểm tra Hit Rate và Token F1.

Không có dữ liệu synthetic nào được ghi đè lên `data/raw/` hoặc `data/clean/`.

## 3. Các tình huống kiểm thử

| STT | Tình huống | Cách kiểm thử | Kết quả mong đợi |
|---:|---|---|---|
| 1 | Sinh benchmark testset | Tạo DataFrame gồm 12 paper hợp lệ | Sinh đúng 10 câu hỏi qua 4 nhóm nghiệp vụ |
| 2 | Thiếu schema | Chỉ truyền cột `paper_id`, thiếu `title`, `summary`, `published` | Phát sinh `ValueError` rõ nguyên nhân |
| 3 | Tích hợp dữ liệu Role B | Chạy raw records → `build_clean_dataframe()` → `build_test_set()` | 24 dòng sạch, `paper_id` duy nhất, sinh đủ 10 câu hỏi |
| 4 | Token F1 | Kiểm tra dấu câu, token lặp và hai câu không có token trùng khớp | F1 lần lượt bằng `0.8` và `0.0` |
| 5 | Câu hỏi summary | Truyền metadata có hai câu summary | Trả về câu đầu tiên |
| 6 | Câu hỏi authors | Truyền `authors_joined` trong metadata | Trả về đúng danh sách tác giả |
| 7 | Câu hỏi date | Truyền `published` trong metadata | Trả về đúng ngày xuất bản |
| 8 | Câu hỏi categories | Truyền `categories_joined` trong metadata | Trả về đúng danh mục |
| 9 | Mock retrieval agent | Stub index trả về một paper cục bộ | Agent trả lời dựa trên context của paper |
| 10 | Provider alias | Đặt `LLM_PROVIDER=google` | Chuẩn hóa thành `gemini` |
| 11 | Evaluation output | Chạy một evaluation sample có retrieval đúng | Hit Rate và Token F1 bằng `1.0` |
| 12 | Semantic retrieval trung thực | Cho exact lookup trả đúng paper nhưng vector search trả sai paper | Evaluation không gọi exact lookup và ghi Hit Rate bằng `0.0` |
| 13 | Baseline report | Truyền metric, quality và freshness đã đo vào report generator | Báo cáo chứa đúng các giá trị, không nhập số liệu thủ công |

## 4. Phân bố benchmark thật

Artifact `data/eval/test_set.json` được sinh từ dữ liệu sạch thật của Role B, không phải dữ liệu giả.

| Loại câu hỏi | Số lượng |
|---|---:|
| `summary` | 3 |
| `authors` | 3 |
| `date` | 2 |
| `categories` | 2 |
| **Tổng** | **10** |

Mười câu hỏi sử dụng 10 `paper_id` khác nhau. Ground truth của từng câu đã được đối chiếu với `data/clean/papers_clean.json`.

## 5. Lệnh chạy test

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_role_d.py
```

## 6. Kết quả

```text
13 passed
0 failed
```

Kết quả xác nhận phần testset, QA extraction, mock agent, provider routing và evaluation metrics của Role D hoạt động đúng với schema dữ liệu của Role B.

## 7. Kết quả baseline end-to-end

Lệnh chạy nghiệm thu không gọi API LLM bên ngoài:

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
.\.venv\Scripts\python.exe script\run_phase1.py
```

Kết quả thực tế trên Chroma semantic search dùng `all-MiniLM-L6-v2`. Evaluation tắt exact-title lookup để Hit Rate phản ánh retrieval thật:

| Chỉ số | Kết quả |
|---|---:|
| Raw records | 24 |
| Clean records | 24 |
| Indexed documents | 24 |
| Evaluation questions | 10 |
| Retrieval Hit Rate | 1.0000 |
| Mean Token F1 | 0.8759 |
| Judge Accuracy | 0.9000 |
| Mean Judge Score | 4.2000 |
| Great Expectations | 7/7 passed |
| Freshness stale ratio | 0.0417 |

Các artifact được tạo:

- `data/results/baseline_metrics.json`
- `data/results/baseline_answers.json`
- `data/results/agent_demo_answers.json`
- `data/reports/phase1_report.md`

## 8. Trạng thái corruption testing

Tại thời điểm ghi log, Role D **chưa tiêm sáu lỗi corruption** vào dataset chính. `src/ingestion/corruption.py` vẫn thuộc phạm vi Role E và chưa có `corruption_log.json` trong `data/results/`.

Các lỗi sau chỉ được ghi là đã thực thi sau khi Role E hoàn thiện và chạy corruption flow:

1. Drop latest records.
2. Blank summary.
3. Inject noise.
4. Truncate title.
5. Stale publication date.
6. Duplicate rows.

Do đó, báo cáo Role D chỉ công bố các kết quả kiểm thử nêu trên và không sử dụng số liệu corruption chưa được thực thi.
