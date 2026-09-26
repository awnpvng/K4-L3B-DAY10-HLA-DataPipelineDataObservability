# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phan Thị Khánh Linh |
| MSSV | 2A202602310 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | HLA |
| Vai trò chính | B — Quality Lead (Cleaning & Observability) |
| Repository | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/artifact phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Clean-data artifacts | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Raw records đã parse từ Crossref | Dataset sạch 24 dòng, có schema ổn định cho retrieval | Hoàn thành |
| Baseline Quality Gate | `data/quality/baseline_quality_report.json` | Clean dataframe | Kết quả kiểm tra row count, ID, title, summary và freshness | Hoàn thành |
| Freshness monitoring | `data/quality/freshness_report.json` | `published`, `age_days` và cấu hình SLA | Báo cáo tuổi dữ liệu, stale ratio và trạng thái `is_fresh` | Hoàn thành |
| Kiểm chứng quality sau corruption/repair | `data/quality/corrupted_quality_report.json`, `data/quality/repaired_quality_report.json` | Hai trạng thái dữ liệu corrupted và repaired | Bằng chứng Quality/Freshness fail rồi phục hồi | Hoàn thành |

Commit cá nhân `e3636ba` (`Add Day 10 data quality outputs`) là bằng chứng trực tiếp cho việc bàn giao clean CSV/JSON, baseline quality report và freshness report. Phần code cuối cùng trong `src/ingestion/cleaning.py` và `src/observability/quality.py` được hoàn thiện qua phối hợp nhóm ở commit `fbf0d7e`; báo cáo này không nhận toàn bộ ownership cá nhân cho commit đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt clean-data contract | Role C — Embedding & Vector Index | Bàn giao `paper_id`, `title`, `summary`, `published`, `age_days`, `text_for_embedding` và metadata cần thiết để index |
| Đối chiếu dữ liệu corrupted/repaired | Role E — Corruption & Repair | Xác nhận Quality Gate phát hiện đúng các lỗi và trở lại PASS sau khi rebuild từ raw lineage |
| Cung cấp tín hiệu baseline | Role D — Agent/Evaluation | Baseline chỉ được đánh giá trên dataset đã qua Quality/Freshness checks |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Sinh và bàn giao clean dataset | `data/clean/papers_clean.csv`, `papers_clean.json` | 24 bản ghi sạch, có `text_for_embedding` và `age_days` | Kiểm tra số dòng, schema và commit `e3636ba` |
| Chạy baseline Quality Gate | `baseline_quality_report.json` | `success: true`, `gx_success: true`, 7/7 expectations PASS | Đọc trực tiếp quality artifact |
| Kiểm tra Freshness SLA | `freshness_report.json` và trường `freshness` trong quality report | 1/24 dòng stale, stale ratio 4.17%, thấp hơn SLA 25%, `is_fresh: true` | Đối chiếu `threshold_days: 180` và `sla_ratio: 0.25` |
| Xác minh corrupted data | `corrupted_quality_report.json` | FAIL: 21 dòng; DOI trùng; 2 title quá ngắn; 2 summary rỗng; stale ratio 38.10% | Đọc từng expectation và freshness payload |
| Xác minh repaired data | `repaired_quality_report.json` | 24 dòng, 7/7 expectations PASS, stale ratio trở lại 4.17% | So sánh cùng schema và cùng ngưỡng với baseline |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một pipeline RAG vẫn có thể chạy và trả lời dù dữ liệu đầu vào đã mất dòng, trùng DOI, rỗng summary hoặc quá cũ. Đây là silent failure: lỗi không nhất thiết làm chương trình crash nhưng làm retrieval và answer quality suy giảm. Role B tạo clean-data contract và các tín hiệu observability để chặn hoặc cảnh báo dữ liệu không đạt trước khi đưa vào vector index.

### Cách triển khai

Luồng cleaning chuẩn hóa HTML/JATS và whitespace, đưa `paper_id` về chữ thường, parse ngày theo UTC, bỏ record thiếu ID/title/summary/ngày xuất bản và khử trùng lặp theo `paper_id` bằng cách giữ bản cập nhật mới nhất. Các trường danh sách tác giả và category được làm sạch, loại phần tử trùng nhưng vẫn giữ thứ tự. Pipeline tính `summary_chars`, `age_days` và ghép title, authors, published date, categories, summary thành `text_for_embedding`.

Quality Gate dùng Great Expectations 1.x với ephemeral context. Trước khi chạy expectation, code kiểm tra các cột bắt buộc. Bảy checks hiện tại bao gồm:

- row count phải đúng số lượng kỳ vọng 24;
- `paper_id` không null và unique;
- `title` không null, độ dài từ 8 đến 500;
- `summary` không null, độ dài từ 40 đến 10.000.

Freshness được đánh giá riêng nhưng gộp vào trạng thái tổng. Một record được xem là stale khi `age_days > 180`; dataset chỉ PASS khi stale ratio không vượt 25%. Vì vậy `success` chỉ là `true` khi cả GX checks và Freshness SLA cùng đạt.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Danh sách `PaperRecord` từ raw lineage; `run_date`; cấu hình `max_results = 24`, freshness threshold 180 ngày |
| Output | Clean CSV/JSON; baseline/corrupted/repaired quality report; standalone freshness report |
| Module phụ thuộc | `src/ingestion/crossref.py`, `src/core/config.py`, `pandas`, Great Expectations 1.x |
| Module sử dụng output | `src/retrieval/index.py`, evaluation pipeline, corruption/repair flow và reporting |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc, record thiếu trường quan trọng, ngày không hợp lệ, DOI trùng, title/summary sai độ dài, row count lệch hoặc stale ratio vượt SLA |

### Cách xác minh

```powershell
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean rows = {len(df)}')"

python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); result=run_data_quality_checks(df, s, 'test'); print(result['success'], result['row_count'], result['freshness']['stale_ratio'])"
```

- **Kết quả mong đợi:** clean dataset có 24 dòng; baseline quality trả `True`; stale ratio không vượt 0.25.
- **Kết quả thực tế trong artifact:** baseline có 24 dòng, 7/7 expectations PASS, stale ratio `0.041666...` và `is_fresh: true`.
- **Artifact/log:** `data/clean/papers_clean.*`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Artifact ban đầu chỉ kiểm tra row count trong khoảng rất rộng từ 1 đến 100.000. Điều kiện này vẫn PASS nếu corruption làm dataset giảm từ 24 xuống 21 dòng, nên không phát hiện được mất dữ liệu.
- **Các phương án đã cân nhắc:** giữ range rộng để tái sử dụng cho nhiều lần fetch; dùng tỷ lệ sai lệch cho phép; hoặc buộc row count đúng `settings.max_results` trong bài lab cố định 24 records.
- **Phương án đã chọn:** đặt cả `min_value` và `max_value` bằng `settings.max_results`.
- **Lý do:** mục tiêu của thí nghiệm là so sánh ba trạng thái trên cùng corpus. Chỉ cần mất một phần dữ liệu cũng có thể làm mất ground-truth document, vì vậy fail-closed phù hợp hơn sự linh hoạt của range rộng.
- **Bằng chứng quyết định phù hợp:** corrupted dataset còn 21 dòng và Quality Gate chuyển sang FAIL; baseline và repaired đều đủ 24 dòng và PASS.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** trong artifact quality ban đầu ở commit `e3636ba`, mỗi chi tiết expectation nằm trong trường `result` dưới dạng chuỗi JSON thay vì object JSON có cấu trúc.
- **Bước tái hiện:** đọc `expectations[0].result` của artifact ở commit trên và kiểm tra kiểu dữ liệu; nội dung bắt đầu bằng chuỗi `{"success": ...}`.
- **Nguyên nhân gốc:** kết quả Great Expectations đã bị stringify trước khi ghi report, tạo double serialization và khiến downstream phải parse JSON thêm lần nữa.
- **Cách xử lý:** trong lần tích hợp nhóm, chuyển từng validation result bằng `result.to_json_dict()` trước khi ghi file.
- **Cách xác minh sau khi sửa:** trong `data/quality/baseline_quality_report.json` hiện tại, mỗi phần tử `expectations` là object và có thể truy cập trực tiếp các trường `success`, `expectation_config` và `result.observed_value`.
- **Điều học được:** artifact observability không chỉ cần “đọc được bằng mắt”; schema của report phải có cấu trúc ổn định để pipeline khác có thể truy vấn tự động.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được parse thành raw `PaperRecord` và lưu nguyên bản để giữ lineage. Cleaning biến raw records thành dataframe có schema ổn định, tính `age_days` và `text_for_embedding`. Quality/Freshness kiểm tra dataframe trước khi Role C sinh embeddings và nạp vào ChromaDB.
2. Evaluation set giữ câu hỏi, answer tham chiếu và `ground_truth_doc_ids`. Retrieval Hit Rate kiểm tra top-k có chứa ID đúng hay không; Token F1 và judge metrics đánh giá câu trả lời được tạo từ context tìm thấy.
3. Quality checks đo tính đầy đủ, duy nhất, row count và ràng buộc độ dài/schema. Freshness monitoring đo tuổi dữ liệu theo thời gian và tỷ lệ record vượt ngưỡng 180 ngày. Một dataset có thể đúng schema nhưng vẫn quá cũ.
4. Cùng test set giúp cô lập tác động của dữ liệu: nếu thay cả câu hỏi hoặc ground truth giữa ba lần chạy thì không thể kết luận metric giảm do corruption.
5. Repair thành công khi dữ liệu được rebuild từ raw lineage, clean artifacts trở lại 24 dòng, Quality/Freshness từ FAIL trở lại PASS và downstream metrics phục hồi so với trạng thái corrupted.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired + optimized | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Mất 5 record mới nhất làm một số ground-truth document không còn trong corpus; quality row-count check phát hiện vấn đề trước khi nhìn thấy suy giảm retrieval. |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | Summary rỗng/nhiễu và context sai làm answer overlap giảm; dữ liệu repaired cùng bước tối ưu retrieval đưa chỉ số phục hồi. |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | Khi context kém tin cậy, số câu trả lời được judge đánh đúng giảm từ 9/10 xuống 8/10. |
| `mean_judge_score` | 4.2000 | 3.8000 | 5.0000 | Xu hướng giảm và phục hồi nhất quán với Retrieval Hit Rate và Token F1. |
| Quality checks | PASS (7/7) | FAIL | PASS (7/7) | Corrupted report phát hiện row count 21, 4 giá trị DOI thuộc các nhóm trùng, 2 title quá ngắn và 2 summary rỗng. |
| Freshness status | PASS (4.17%) | FAIL (38.10%) | PASS (4.17%) | Sáu ngày xuất bản bị lùi một năm làm tổng số stale records tăng lên 8/21, vượt SLA 25%. |

### Kết luận từ số liệu

1. Drop records, duplicate rows, truncate title, blank summary và stale dates → GX checks FAIL, stale ratio tăng từ 4.17% lên 38.10% → Retrieval Hit Rate giảm từ 1.0 xuống 0.6, Token F1 giảm còn 0.8213 và judge score giảm còn 3.8.
2. Rebuild clean data từ raw lineage → 24 dòng, 7/7 checks PASS và stale ratio trở lại 4.17% → Retrieval Hit Rate phục hồi 1.0; ở trạng thái repaired có thêm tối ưu retrieval, Token F1 và judge accuracy đạt 1.0.

Corruption ảnh hưởng rõ nhất đến observability là kết hợp `drop_latest_records` và `stale_date`: một lỗi làm row count lệch, lỗi còn lại đẩy Freshness SLA vượt ngưỡng. Đối với agent, việc drop tài liệu nghiêm trọng nhất vì document đã bị xóa thì retrieval không thể lấy lại dù embedding model vẫn hoạt động đúng.

Một kết quả đáng chú ý là expectation “summary không null” vẫn PASS với chuỗi rỗng. Đây không phải lỗi của GX: empty string khác `null`. Check độ dài summary mới bắt đúng hai dòng rỗng. Điều này chứng minh một rule đơn lẻ chưa đủ; cần kết hợp nullability với semantic constraints như độ dài tối thiểu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Clean-data contract phải ổn định vì mọi thay đổi ở ID, ngày hoặc `text_for_embedding` đều ảnh hưởng retrieval và evaluation downstream.
2. Data observability cần nhiều tín hiệu bổ sung cho nhau: schema, completeness, uniqueness, length, volume và freshness không thể thay thế lẫn nhau.
3. Pipeline không crash không đồng nghĩa dữ liệu đúng; Quality Gate cần chạy trước serving/indexing để biến silent failure thành tín hiệu có thể hành động.

### Nếu có thêm thời gian

Tôi sẽ bổ sung rule phát hiện noise pattern, kiểm tra URL/date range, lưu dataset hash trong quality report và thêm cảnh báo theo severity. Cải thiện được xem là đạt khi từng corruption scenario kích hoạt đúng rule chuyên biệt, report chỉ ra chính xác các row/field bị ảnh hưởng và pipeline có thể fail-fast trước bước embedding.

## 10. Cam kết của thành viên

Phần này cần Phan Thị Khánh Linh tự đọc lại và đánh dấu trước khi nộp:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Thị Khánh Linh

**Ngày xác nhận:** 2026-09-26
