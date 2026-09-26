# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trương Hoàng Thành An |
| MSSV | 2A202602574 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | HLA |
| Vai trò chính | A — Data Lead (Ingestion & Raw Lineage) |
| Repository | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref payload parsing | `src/ingestion/crossref.py` → `parse_crossref_payload()` | JSON response Crossref (`message.items`) | `list[PaperRecord]` (10 field chuẩn hóa) | Hoàn thành |
| Source fetching + fallback | `src/ingestion/crossref.py` → `fetch_source_records()` | `Settings` (query, filter, max_results) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Raw snapshot loading | `src/ingestion/crossref.py` → `load_raw_records()` | Đường dẫn JSON snapshot | `list[PaperRecord]` | Hoàn thành |

Đây là 3 hàm tôi trực tiếp implement; toàn bộ module `cleaning.py`, `quality.py`, `embeddings.py`, `index.py`, `agent.py`, `llm.py`, `qa.py`, `testset.py`, `corruption.py` do B/C/D/E phụ trách, tôi không chỉnh sửa logic của họ.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Dựng `.venv`, verify môi trường chạy được ở Checkpoint 0 | Cả nhóm | Cả 4 thành viên xác nhận `import chromadb, great_expectations, sentence_transformers` chạy OK trước khi bắt đầu code song song |
| Thống nhất schema `PaperRecord` (10 field) trước khi B viết `cleaning.py` | B — Nguyễn Thị Bảo Trang | B viết `build_clean_dataframe` đọc đúng field `published`, `authors`, `categories` ngay từ đầu, không phải sửa lại |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse Crossref payload đúng schema | `parse_crossref_payload()` | 24/24 `PaperRecord` hợp lệ | `python -c "from ingestion.crossref import parse_crossref_payload; ..."` |
| Fetch + lưu raw artifact | `fetch_source_records()` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | `python script/run_phase1.py` chạy tới bước ingestion không lỗi |
| Tín hiệu nghiệm thu CP0 | `fetch_source_records(settings)` | Console in `Tín hiệu hoàn thành: Đã tải 24 bài báo` | Lệnh nghiệm thu trong `docs/CHECKPOINTS.md` mục CP0 |

Output cụ thể: `data/raw/crossref_records.json` chứa đúng 24 bản ghi `PaperRecord` với đầy đủ field (`paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`) — đây là input duy nhất mà `build_clean_dataframe` (B) và toàn bộ luồng repair (E) đọc vào.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết bước đầu tiên của pipeline: lấy dữ liệu metadata bài báo từ nguồn ngoài (Crossref API) một cách đáng tin cậy, chuẩn hóa thành cấu trúc cố định (`PaperRecord`), và bảo toàn bản ghi gốc để các bước sau (cleaning, repair) luôn có một "nguồn sự thật" (source of truth) để quay về khi dữ liệu bị hỏng.

### Cách triển khai

- `parse_crossref_payload()`: duyệt `payload["message"]["items"]`, bóc tag JATS (`<jats:p>...</jats:p>`) khỏi `abstract` bằng regex `<[^>]+>` rồi chuẩn hóa khoảng trắng, ghép `given + family` thành tên đầy đủ cho từng tác giả (bỏ qua nếu cả hai trống), lấy `subject[0]` làm `primary_category`, và chuẩn hóa `date-parts` (dạng `[[year, month, day]]`, có thể thiếu month/day) thành chuỗi ISO `YYYY-MM-DD`. Record bị bỏ nếu thiếu DOI hoặc title vì đây là 2 trường bắt buộc để định danh và hiển thị.
- `fetch_source_records()`: gọi Crossref REST API với `params` lấy từ `Settings` (`query.bibliographic`, `filter`, `rows`), retry tối đa 3 lần với backoff `2**attempt` giây khi gặp lỗi mạng hoặc HTTP 429/503. Nếu vẫn thất bại, fallback đọc lại `raw_api_response` (snapshot HTTP response cũ) hoặc cuối cùng là `raw_records_json` (đã parse sẵn) để pipeline không bao giờ bị chặn hoàn toàn vì lỗi mạng.
- Tôn trọng cờ `settings.refresh_source`: mặc định `False` để ưu tiên dùng lại snapshot đã lưu (đảm bảo kết quả tái lập được giữa các lần chạy), chỉ gọi API mới khi được yêu cầu tường minh.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | JSON response từ `https://api.crossref.org/works` theo cấu trúc `{"message": {"items": [...]}}` |
| Output | `list[PaperRecord]` (dataclass 10 field) + 2 file JSON: `data/raw/crossref_response.json` (raw), `data/raw/crossref_records.json` (đã parse) |
| Module phụ thuộc | `core.config.Settings` (query/filter/paths), `core.utils` (`write_json`, `read_json`, `normalize_whitespace`) |
| Module sử dụng output | `src/ingestion/cleaning.py` (B) đọc `PaperRecord` làm input cho `build_clean_dataframe`; `src/ingestion/corruption.py`/`run_corruption_flow.py` (E) đọc lại `crossref_records.json` làm nguồn rebuild khi repair |
| Điều kiện lỗi cần xử lý | Mất mạng/API rate-limit (429/503) → retry rồi fallback offline; record thiếu DOI/title → bị loại khỏi kết quả thay vì crash toàn bộ batch |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

- **Kết quả mong đợi:** Console in `Tín hiệu hoàn thành: Đã tải 24 bài báo` (theo `docs/CHECKPOINTS.md`).
- **Kết quả thực tế:** Đúng như mong đợi, in ra 24 bài báo, chạy trên `.venv` local không lỗi.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (không chứa secret, chỉ chứa metadata công khai từ Crossref).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cơ chế fallback khi Crossref API lỗi hoặc mất mạng trong lúc demo trên lớp — pipeline không được phép dừng hoàn toàn.
- **Các phương án đã cân nhắc:**
  1. Chỉ raise exception khi API lỗi, bắt buộc phải có mạng ổn định lúc chạy.
  2. Retry vài lần rồi fallback đọc lại snapshot JSON cục bộ đã lưu từ lần chạy trước.
- **Phương án đã chọn:** Phương án 2 — retry 3 lần (backoff cho 429/503) rồi fallback theo thứ tự `raw_api_response` → `raw_records_json`.
- **Lý do:** Ưu tiên tính sẵn sàng (availability) của pipeline trong buổi live demo trên lớp hơn là luôn phải có dữ liệu "tươi nhất"; đồng thời theo đúng yêu cầu CP0 trong `docs/CHECKPOINTS.md` là phải "hỗ trợ cơ chế fallback đọc từ snapshot local khi mất mạng hoặc dính 429".
- **Bằng chứng quyết định phù hợp:** Chạy `fetch_source_records()` với `refresh_source=False` (mặc định) vẫn trả về đủ 24 bản ghi từ snapshot mà không cần gọi mạng, xác nhận qua console `Tín hiệu hoàn thành: Đã tải 24 bài báo`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi test `fetch_source_records()` với biến môi trường `REFRESH_SOURCE=1` để kiểm tra nhánh gọi API thật, 2 file `data/raw/crossref_response.json` và `data/raw/crossref_records.json` bị ghi đè hoàn toàn bằng dữ liệu Crossref khác (DOI, tiêu đề, tác giả khác hẳn 24 bài báo fixture chuẩn dùng để chấm điểm).
- **Lệnh hoặc bước tái hiện:** `REFRESH_SOURCE=1 python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; fetch_source_records(load_settings())"`.
- **Nguyên nhân gốc:** Crossref API không deterministic — cùng một query nhưng gọi ở các thời điểm khác nhau trả về tập kết quả khác nhau (do có bài báo mới được index liên tục), trong khi `fetch_source_records()` khi `refresh_source=True` sẽ ghi đè trực tiếp lên 2 file raw mà không tạo bản backup.
- **Cách xử lý:** Revert 2 file về đúng bản gốc bằng `git checkout -- data/raw/crossref_records.json data/raw/crossref_response.json`, đồng thời thống nhất với nhóm là **không set `REFRESH_SOURCE=1`** khi chạy chính thức để nộp bài/demo, giữ `refresh_source=False` mặc định.
- **Cách xác minh sau khi sửa:** `git status --short data/raw/` không còn thay đổi; chạy lại `fetch_source_records()` mặc định (không set `REFRESH_SOURCE`) vẫn trả về đúng 24 bài báo cố định như fixture ban đầu.
- **Điều học được:** Dữ liệu lấy từ API bên thứ ba không nên được coi là nguồn "raw" ổn định cho việc chấm điểm/tái lập — cần tách rõ giữa "raw snapshot cố định dùng để test/chấm điểm" và "chế độ refresh dùng khi vận hành thật", tránh vô tình làm mất tính idempotent của toàn bộ pipeline.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Dữ liệu đi từ Crossref API qua `fetch_source_records()` → được `parse_crossref_payload()` chuẩn hóa thành `PaperRecord` → B đọc vào `build_clean_dataframe()` để khử trùng lặp, tính `age_days`, ghép `text_for_embedding` → C dùng `text_for_embedding` sinh vector bằng `all-MiniLM-L6-v2` và nạp vào ChromaDB collection `papers-baseline`.
2. Evaluation set (`data/eval/test_set.json`, 10 câu hỏi) được D sinh ra với `ground_truth_doc_ids` gắn trực tiếp theo DOI (`paper_id`) của bài báo nguồn; khi Agent trả lời, hệ thống so khớp document ID retrieve được với `ground_truth_doc_ids` để tính Retrieval Hit Rate, và so khớp câu trả lời với `ground_truth` để tính Token F1.
3. Quality checks (Great Expectations) kiểm tra cấu trúc/tính hợp lệ của dữ liệu tại một thời điểm cụ thể (row count, null, unique, độ dài) — trả lời câu hỏi "dữ liệu hiện tại có đúng schema/chuẩn không". Freshness monitoring kiểm tra khía cạnh thời gian — trả lời câu hỏi "dữ liệu này có còn mới không" dựa vào tỷ lệ bài báo có `age_days > 180`. Một dataset có thể pass Quality Gate (đúng cấu trúc) nhưng vẫn fail Freshness (dữ liệu cũ), như trường hợp `stale_date` corruption.
4. Phải dùng cùng test set cho cả 3 trạng thái (baseline/corrupted/repaired) vì nếu câu hỏi khác nhau, chênh lệch Hit Rate/F1 có thể do câu hỏi khác nhau khó/dễ khác nhau chứ không phải do corruption/repair — sẽ không còn là so sánh công bằng (apples-to-apples).
5. Repair được coi là thành công khi đồng thời: (a) Quality Gate và Freshness SLA quay lại PASS trong `repaired_quality_report.json`, và (b) các metric agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) trong `repaired_metrics.json` phục hồi về bằng hoặc vượt mức baseline — chỉ một trong hai điều kiện là chưa đủ bằng chứng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Phục hồi hoàn toàn, chứng tỏ rebuild từ raw snapshot của phần A giữ nguyên đúng 24 bài báo gốc |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | Repaired vượt baseline nhờ hybrid reranker của E, không phải do raw data thay đổi |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | Cùng xu hướng phục hồi như Hit Rate |
| `mean_judge_score` | 4.2000 | 3.8000 | 5.0000 | Phục hồi và vượt baseline |
| Quality checks | PASS (7/7) | FAIL | PASS (7/7) | FAIL chủ yếu do row count 21≠24, đúng như raw lineage anchor của A vẫn giữ 24 bản ghi để đối chiếu |
| Freshness status | PASS (4.17%) | FAIL (38.10%) | PASS (4.17%) | `stale_date` là nguyên nhân chính, không liên quan tới phần ingestion của tôi vì raw data gốc không có bài nào lệch ngày |

### Kết luận từ số liệu

1. `drop_latest_records` + `stale_date` làm row count giảm còn 21/24 và stale ratio tăng 4.17%→38.10% → Freshness SLA và Quality Gate chuyển PASS→FAIL → Retrieval Hit Rate giảm 1.0000→0.6000, rõ nhất ở nhóm câu hỏi `date` (Hit Rate 1.0000→0.0000, vì các bài báo mới nhất — vốn là ground truth của câu hỏi ngày tháng — đã bị xóa hoặc lùi ngày).
2. Repair đọc lại `data/raw/crossref_records.json` (không đổi trong suốt buổi lab, do tôi bảo toàn) → Freshness và Quality Gate quay lại đúng số liệu baseline (stale ratio 4.17%, row count 24) → toàn bộ metric agent phục hồi về hoặc vượt baseline.

Corruption ảnh hưởng rõ nhất: `stale_date` (6/21 bản ghi, chiếm tỷ trọng lớn nhất trong 6 kịch bản) — vì nó tác động trực tiếp đến Freshness SLA (biến PASS thành FAIL với biên độ lớn nhất, +33.93 điểm phần trăm stale ratio) và kéo theo Retrieval Hit Rate của nhóm câu hỏi `date` về 0.

Kết quả khác kỳ vọng ban đầu: Mean Token F1 sau repair (1.0000) cao hơn cả baseline (0.8759) thay vì chỉ bằng — giả thuyết ban đầu của tôi là do lỗi tính toán trùng lặp, nhưng đối chiếu `corruption_report.md` cho thấy đây là do E chủ động thêm bước "hybrid title reranker" ở giai đoạn hậu-repair, không liên quan đến phần raw data của tôi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot ("lineage anchor") phải được coi là bất biến trong suốt vòng đời của một lần chấm điểm/demo — bất kỳ thao tác nào vô tình ghi đè nó (như gọi API refresh) đều phá vỡ khả năng tái lập của toàn bộ pipeline phía sau, kể cả khi logic các module khác hoàn toàn đúng.
2. Data quality không chỉ là "đúng cấu trúc" (schema/null/unique) mà còn phải tách riêng chiều "thời gian" (freshness) — hai khía cạnh này có thể độc lập PASS/FAIL với nhau.
3. Một lỗi ở tầng ingestion (raw data sai/thiếu) sẽ lan truyền âm thầm qua toàn bộ pipeline (cleaning → embedding → agent) mà không hề crash — đây chính là bản chất của "Silent Failure" mà bài lab minh họa.

### Nếu có thêm thời gian

Tôi sẽ thêm một bước checksum/hash cho `data/raw/crossref_response.json` ngay sau khi fetch, lưu vào một file `raw_manifest.json` riêng; trước mỗi lần chạy `run_phase1.py`, so sánh hash hiện tại với manifest để cảnh báo sớm nếu ai đó vô tình làm thay đổi raw snapshot (đo được bằng cách so sánh `hash` cũ/mới trong log, thay vì phải phát hiện thủ công qua `git diff` như tôi đã làm).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trương Hoàng Thành An
**Ngày xác nhận:** 2026-09-26
