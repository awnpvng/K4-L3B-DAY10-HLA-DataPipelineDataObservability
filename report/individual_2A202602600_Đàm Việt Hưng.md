# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đàm Việt Hưng       |
| MSSV               | 2A202602600                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | HLA     |
| Vai trò chính    | D — Agent/Eval Lead (QA Agent & Evaluation)                 |
| Repository         | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Multi-provider QA Agent | `src/retrieval/agent.py`, `llm.py`, `qa.py` | Câu hỏi + kết quả retrieve từ ChromaDB (C) | `data/results/baseline_answers.json`, `agent_demo_answers.json` | Hoàn thành |
| Benchmark test set & evaluation | `src/evaluation/testset.py`, `metrics.py` | Clean dataframe (B) | `data/eval/test_set.json` (10 câu), `data/results/baseline_metrics.json` | Hoàn thành |
| Post-repair retrieval optimization | `src/retrieval/index.py`, `src/pipelines/corruption_flow.py` | Repaired Chroma index và các ứng viên semantic top-k | `data/results/repaired_answers.json`, `repaired_metrics.json` | Hoàn thành |

QA Agent hỗ trợ các provider `mock`, `google/gemini`, `openai`, `anthropic`, `openrouter`, `ollama` và endpoint tùy chỉnh. Chế độ `mock` được dùng khi nghiệm thu để kết quả có thể tái lập mà không phụ thuộc API key hoặc dịch vụ bên ngoài.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra contract dữ liệu sạch trước khi sinh benchmark | Role B — Cleaning & Observability | Xác nhận 24 dòng, `paper_id` duy nhất và đủ các trường `authors_joined`, `categories_joined`, `text_for_embedding`; xem `test_role_b_clean_dataframe_builds_role_d_testset` |
| Tích hợp Agent/Evaluation vào baseline pipeline | Role C — Vector Index và pipeline chung | Nối Chroma index với `evaluate_pipeline()`, sinh tự động metrics, answers và `phase1_report.md` |
| Cung cấp evaluation và title reranking cho luồng repair | Role E — Resilience | Đánh giá cùng test set ở ba trạng thái; sau repair, rerank các ứng viên semantic giúp Token F1 đạt 1.0000 mà không dùng full-corpus exact lookup |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 10 câu hỏi test phủ 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) | `src/evaluation/testset.py` | `data/eval/test_set.json` | Lệnh nghiệm thu CP2 trong `docs/CHECKPOINTS.md` |
| Xây router Agent đa provider và đo Hit Rate/Token F1 | `src/retrieval/agent.py`, `src/evaluation/metrics.py` | `data/results/baseline_metrics.json` (Hit Rate 1.0000, F1 0.8759, Judge Accuracy 0.9000) | `python script/run_phase1.py` |
| Viết test cho testset, QA, mock agent, provider alias, metrics và báo cáo | `tests/test_role_d.py`, `docs/ROLE_D_TEST_LOG.md` | 13 trường hợp kiểm thử đều đạt | `python -m pytest -q -p no:cacheprovider tests/test_role_d.py` |
| Cải thiện top-1 sau repair bằng hybrid title reranking | `TitleRerankedIndex`, `corruption_flow.py` | F1 1.0000, Judge Accuracy 1.0000, Judge Score 5.0000 | `python script/run_corruption_flow.py` và `data/reports/corruption_report.md` |

Output cụ thể: `data/results/baseline_metrics.json` với `retrieval_hit_rate: 1.0`, `mean_token_f1: 0.8759`, `judge_accuracy: 0.9`, `mean_judge_score: 4.2` — là bằng chứng trực tiếp cho tiêu chí #5 (Multi-Provider QA Agent) và #6 (Baseline Evaluation) trong `docs/RUBRIC.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline của nhóm đã có dữ liệu sạch và vector index, nhưng vẫn cần một lớp biến kết quả retrieval thành câu trả lời có căn cứ và một cơ chế đánh giá định lượng. Phần tôi phụ trách giải quyết ba câu hỏi: Agent có tìm đúng tài liệu không, câu trả lời có khớp ground truth không, và khi dữ liệu bị corruption thì chất lượng suy giảm bao nhiêu. Kết quả phải tái lập được, không phụ thuộc vào việc có API key và không được dùng exact lookup để làm đẹp semantic retrieval.

### Cách triển khai

Tôi triển khai theo bốn lớp:

1. `build_test_set()` kiểm tra schema đầu vào, loại paper thiếu ID/tiêu đề, khử trùng lặp và sắp xếp ổn định. Hàm tạo đúng 10 câu hỏi gồm 3 `summary`, 3 `authors`, 2 `date`, 2 `categories`; mỗi câu lưu ground truth và `ground_truth_doc_ids`.
2. `answer_question()` nhận câu hỏi, gọi semantic search top-4 và trích xuất câu trả lời theo loại thông tin trong metadata. Exact-title lookup chỉ được dùng cho luồng hỏi đáp thông thường; trong evaluation, tham số `use_exact_lookup=False` bảo đảm đo retrieval thật.
3. `evaluate_pipeline()` tính Retrieval Hit Rate, Token F1, Judge Accuracy và Mean Judge Score; đồng thời lưu chi tiết câu trả lời, tài liệu đã retrieve và kết quả theo từng loại câu hỏi. Ragas được để ở chế độ tùy chọn vì chi phí và thời gian chạy cao hơn.
4. Sau repair, `TitleRerankedIndex` chỉ sắp xếp lại các ứng viên đã được vector search trả về bằng độ liên quan tiêu đề. Nó không tìm trực tiếp trên toàn corpus. Nhờ đưa đúng paper từ top-k lên top-1, F1 và judge metrics cao hơn baseline mà vẫn giữ đánh giá semantic trung thực.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input | DataFrame sạch có `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `text_for_embedding`; Chroma index; cấu hình provider; test set JSON |
| Output | Câu trả lời có `retrieved_doc_ids`/contexts; `test_set.json`; các file `*_answers.json`, `*_metrics.json`; báo cáo baseline và comparison |
| Module phụ thuộc | `ingestion.cleaning` của Role B, `retrieval.index`/`embeddings` của Role C, `core.config` và dữ liệu raw của Role A |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, reporting và phần phân tích repair của Role E |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc, test set rỗng, câu hỏi rỗng, index không trả kết quả, thiếu credential, LLM judge/Ragas không khả dụng và nguy cơ exact lookup làm sai lệch evaluation |

### Cách xác minh

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_role_d.py
```

- **Kết quả mong đợi:** Sinh 10 câu hỏi hợp lệ; index 24 paper; Agent trả lời dựa trên context; Hit Rate và Token F1 được ghi tự động; toàn bộ test Role D đạt.
- **Kết quả thực tế:** 24/24 paper được index, 10 câu hỏi được đánh giá, Retrieval Hit Rate 1.0000, Mean Token F1 0.8759, Judge Accuracy 0.9000, Mean Judge Score 4.2000 và 13/13 test đạt.
- **Artifact/log:** `data/eval/test_set.json`, `data/results/baseline_answers.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, `docs/ROLE_D_TEST_LOG.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Các câu benchmark chứa tiêu đề paper trong dấu nháy. Nếu Agent tra cứu chính xác theo tiêu đề trước khi semantic search thì kết quả có thể đạt điểm cao dù vector retrieval hoạt động kém.
- **Các phương án đã cân nhắc:** (1) giữ exact lookup để câu trả lời dễ đúng; (2) tắt exact lookup hoàn toàn; (3) tắt exact lookup trong evaluation nhưng vẫn cho phép ở luồng Agent thông thường.
- **Phương án đã chọn:** Phương án 3. `evaluate_pipeline()` luôn gọi `answer_question(..., use_exact_lookup=False)`; Agent demo vẫn có thể dùng lookup như một tool hợp lệ.
- **Lý do:** Tách trải nghiệm sử dụng thực tế khỏi phép đo benchmark. Evaluation phản ánh trung thực chất lượng embedding/vector search, trong khi Agent vẫn có khả năng xử lý truy vấn định danh rõ ràng.
- **Bằng chứng quyết định phù hợp:** Test `test_evaluation_does_not_force_exact_title_lookup` cấu hình lookup trả đúng nhưng semantic search trả sai; evaluation không gọi lookup và ghi nhận Hit Rate 0.0 như mong đợi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Với câu hỏi có tiêu đề trong dấu nháy, QA có thể lấy đúng paper bằng `lookup()` ngay cả khi semantic search xếp sai tài liệu. Khi đó Hit Rate không còn phản ánh chất lượng retrieval thật.
- **Lệnh hoặc bước tái hiện:** Tạo stub index trong đó `lookup()` có thể trả paper đúng nhưng `search()` chỉ trả paper sai, sau đó chạy `evaluate_pipeline()`.
- **Nguyên nhân gốc:** `answer_question()` mặc định ưu tiên exact-title lookup để phục vụ hỏi đáp, trong khi evaluation cần đo độc lập semantic retrieval.
- **Cách xử lý:** Bổ sung cờ `use_exact_lookup`; evaluation đặt giá trị `False` và chỉ tính Hit Rate trên danh sách do vector search trả về.
- **Cách xác minh sau khi sửa:** Chạy `python -m pytest -q -p no:cacheprovider tests/test_role_d.py`; kết quả `13 passed`, trong đó test semantic retrieval ghi đúng Hit Rate 0.0 cho tình huống search sai.
- **Điều học được:** Một pipeline có thể chạy đúng về mặt chức năng nhưng phép đo vẫn sai nếu benchmark vô tình đi đường tắt. Metric chỉ có ý nghĩa khi đường đánh giá khớp với năng lực cần đo.

## 7. Hiểu biết về luồng end-to-end

1. **Từ Crossref đến vector index:** Dữ liệu được lấy từ Crossref API hoặc raw snapshot, lưu lại để bảo toàn lineage, sau đó cleaning loại tag/khoảng trắng, khử trùng lặp, tính `age_days` và tạo `text_for_embedding`. Quality Gate kiểm tra dữ liệu trước khi MiniLM sinh embedding và ChromaDB lưu 24 document cùng metadata.
2. **Cách evaluation hoạt động:** Mỗi câu hỏi có đáp án chuẩn và danh sách `ground_truth_doc_ids`. Retrieval Hit Rate kiểm tra paper đúng có nằm trong top-4 hay không; Token F1 so sánh token của câu trả lời với ground truth; judge đánh giá mức đúng về ngữ nghĩa. Chi tiết từng mẫu được lưu để truy ngược nguyên nhân.
3. **Quality và freshness:** Quality checks đo tính đầy đủ, hợp lệ, duy nhất và đúng schema tại thời điểm chạy. Freshness monitoring tập trung vào tuổi dữ liệu, tính tỷ lệ paper có `age_days > 180` và so sánh với SLA 25%. Một dataset có thể đúng schema nhưng vẫn quá cũ.
4. **Giữ nguyên test set:** Baseline, corrupted và repaired phải dùng cùng câu hỏi, đáp án và document ID để thay đổi metric phản ánh thay đổi dữ liệu/index, không phải do đổi đề kiểm tra.
5. **Điều kiện repair thành công:** Dữ liệu phục hồi 24 dòng duy nhất, Quality Gate và Freshness SLA trở lại PASS, Hit Rate phục hồi 0.6000 lên 1.0000. Sau clean rebuild và title reranking, F1 đạt 1.0000, Judge Accuracy 1.0000 và Judge Score 5.0000; bằng chứng nằm trong `repaired_metrics.json` và `corruption_report.md`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Hai paper ground truth của nhóm `date` bị `drop_latest_records`, làm Hit Rate của riêng nhóm này giảm từ 1.0000 xuống 0.0000. Repair đưa đủ document trở lại index. |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | Corruption làm top-1 sai hoặc metadata không còn đúng. Rebuild và title reranking đưa đúng paper lên top-1 nên câu trả lời khớp hoàn toàn ground truth. |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | Một số câu trả lời sai ngày/tóm tắt ở trạng thái corrupted; sau repair, cả 10 câu được judge chấp nhận. |
| `mean_judge_score` | 4.2000 | 3.8000 | 5.0000 | Điểm trung bình giảm theo answer quality và đạt tối đa sau khi dữ liệu cùng thứ hạng top-1 được phục hồi. |
| Quality checks | PASS (7/7) | FAIL (row count 21≠24) | PASS (7/7) | Các lỗi thiếu dòng, summary rỗng và DOI trùng làm gate thất bại; rebuild từ raw snapshot phục hồi contract. |
| Freshness status | PASS (4.17%) | FAIL (38.10%) | PASS (4.17%) | Sáu ngày xuất bản bị đẩy lùi một năm làm stale ratio vượt SLA 25%; repaired data trở lại 4.17%. |

*(Số liệu trên lấy từ `data/results/*_metrics.json` — lưu ý riêng nhóm câu hỏi `date` giảm Hit Rate 1.0000→0.0000 khi bị corrupted, xem `by_question_type` trong `corrupted_metrics.json` để phân tích chi tiết theo đúng vai trò Eval Lead.)*

### Kết luận từ số liệu

1. `drop_latest_records` xóa 5 paper, trong đó có cả hai ground-truth paper của nhóm `date`; `stale_date` làm stale ratio tăng lên 38.10% và các lỗi khác phá vỡ completeness/uniqueness → Quality Gate và Freshness SLA chuyển sang FAIL → Hit Rate tổng giảm từ 1.0000 xuống 0.6000, Hit Rate nhóm `date` xuống 0.0000 và F1 tổng còn 0.8213.
2. Auto-repair rebuild từ raw lineage snapshot, chạy lại cleaning, quality, embedding và indexing → row count trở lại 24, Quality Gate/Freshness đều PASS → Hit Rate trở lại 1.0000. Hybrid title reranking tiếp tục cải thiện top-1, đưa F1 từ baseline 0.8759 lên 1.0000 và Judge Score từ 4.2 lên 5.0.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records`, vì nó xóa trực tiếp 5 tài liệu khỏi index, bao gồm hai tài liệu chuẩn của hai câu hỏi `date`. Khi document không tồn tại trong collection corrupted, mọi thuật toán rerank đều không thể khôi phục nó; vì vậy Hit Rate nhóm `date` giảm hoàn toàn xuống 0.0000. `stale_date` là tín hiệu observability nghiêm trọng nhất vì đẩy stale ratio từ 4.17% lên 38.10%, vượt SLA 25%.

**Kết quả khác kỳ vọng:** Baseline có Hit Rate 1.0000 nhưng F1 chỉ 0.8759. Kiểm tra `baseline_answers.json` cho thấy paper đúng luôn có trong top-4, nhưng chưa chắc đứng top-1; QA lại trích câu trả lời từ kết quả đầu tiên, đặc biệt làm F1 của nhóm `date` chỉ đạt 0.5000. Tôi kiểm tra giả thuyết bằng danh sách `retrieved_doc_ids` và bổ sung title reranking trên các ứng viên semantic. Sau repair + rerank, F1 của `date` và `summary` đều đạt 1.0000, chứng minh vấn đề nằm ở thứ hạng top-1 chứ không phải thiếu ground truth.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Một evaluation artifact phải có lineage rõ ràng và deterministic; cùng dữ liệu đầu vào phải sinh cùng câu hỏi, đáp án và kết quả đo để có thể so sánh.
2. **Về observability:** Quality Gate phát hiện lỗi cấu trúc/nội dung, còn Freshness SLA phát hiện dữ liệu hợp lệ nhưng đã cũ; cần cả hai để ngăn silent failure trước khi index phục vụ Agent.
3. **Về RAG Agent:** Hit Rate@k cao chưa bảo đảm câu trả lời đúng. Nếu tài liệu chuẩn chỉ nằm trong top-k nhưng không ở top-1, Agent vẫn có thể lấy sai metadata; vì vậy cần theo dõi đồng thời retrieval, answer metrics và thứ hạng.

### Nếu có thêm thời gian

Tôi sẽ mở rộng benchmark từ 10 lên ít nhất 50 câu, bổ sung câu hỏi không chứa nguyên văn tiêu đề và các trường hợp không có đáp án. Sau đó so sánh vector-only, lexical reranking và cross-encoder reranking bằng Hit Rate@1, MRR, Token F1, latency và chi phí. Cách này kiểm tra liệu mức F1 1.0000 hiện tại có tổng quát hóa hay chỉ phù hợp với bộ test nhỏ có tiêu đề rõ ràng.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đàm Việt Hưng

**Ngày xác nhận:** 2026-09-26
