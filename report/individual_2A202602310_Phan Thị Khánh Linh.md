# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phan Thị Khánh Linh       |
| MSSV               | 2A202602310                     |
| Khóa/Lớp         | K4-L3B              |
| Tên nhóm         | HLA     |
| Vai trò chính    | C — Retrieval Lead (Embedding & Vector Index)                 |
| Repository         | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | [YYYY-MM-DD — điền ngày bạn thực sự hoàn thành]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Embedding model | `src/retrieval/embeddings.py` | `text_for_embedding` từ clean dataframe (B) | `data/embeddings/papers_embeddings.json` (vector `all-MiniLM-L6-v2`) | Hoàn thành |
| Vector store indexing | `src/retrieval/index.py` | Vector embeddings + metadata | ChromaDB local persist `data/chroma/`, collection `papers-baseline`/`papers-corrupted`/`papers-repaired` | Hoàn thành |

*(Ghi rõ nếu bạn còn xử lý thêm tham số retrieval, ví dụ `top_k`, similarity function.)*

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Điền hoạt động hỗ trợ thực tế của bạn] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh vector embedding cho 24 tài liệu sạch | `src/retrieval/embeddings.py` | `data/embeddings/papers_embeddings.json` (24 vector) | `python script/run_phase1.py` |
| Khởi tạo và cô lập 3 collection ChromaDB riêng biệt (baseline/corrupted/repaired) | `src/retrieval/index.py` | `data/chroma/` (3 collection độc lập) | Lệnh nghiệm thu CP2 trong `docs/CHECKPOINTS.md` |

Output cụ thể: `data/chroma/` chứa collection `papers-baseline` với đủ 24 document đã index (đối chiếu với `retrieval_hit_rate: 1.0000` trong `data/results/baseline_metrics.json` — nếu index thiếu/sai, Hit Rate baseline sẽ không thể đạt 1.0000).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

[Phần của bạn giải quyết vấn đề gì trong pipeline?]

### Cách triển khai

[Mô tả thuật toán, quy tắc dữ liệu, orchestration hoặc quyết định chính. Không chỉ chép lại tên hàm.]

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | [Schema, artifact hoặc tham số]           |
| Output                         | [Schema, artifact hoặc giá trị trả về] |
| Module phụ thuộc             | [Module/file liên quan]                    |
| Module sử dụng output        | [Module/file liên quan]                    |
| Điều kiện lỗi cần xử lý | [Trường hợp thực tế]                   |

### Cách xác minh

```bash
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Vấn đề hoặc lựa chọn cần quyết định.]
- **Các phương án đã cân nhắc:** [Ít nhất hai phương án.]
- **Phương án đã chọn:** [Lựa chọn.]
- **Lý do:** [Trade-off về correctness, data quality, reproducibility, cost hoặc độ phức tạp.]
- **Bằng chứng quyết định phù hợp:** [Metric, artifact hoặc kết quả thử nghiệm.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Che toàn bộ secret trước khi ghi.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng.]
- **Cách xử lý:** [Thay đổi cụ thể.]
- **Cách xác minh sau khi sửa:** [Lệnh và kết quả.]
- **Điều học được:** [Bài học kỹ thuật.]

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

[Viết câu trả lời tại đây.]

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0000 |       0.6000 |      1.0000 | [Nhận xét của bạn — góc nhìn Retrieval Lead, vì sao index bị ảnh hưởng khi row count giảm 24→21?]              |
| `mean_token_f1`      |      0.8759 |       0.8213 |      1.0000 | [Nhận xét]              |
| `judge_accuracy`     |      0.9000 |       0.8000 |      1.0000 | [Nhận xét]              |
| `mean_judge_score`   |      4.2000 |       3.8000 |      5.0000 | [Nhận xét]              |
| Quality checks         |      PASS (7/7) |       FAIL (row count 21≠24) |      PASS (7/7) | [Nhận xét]              |
| Freshness status       |      PASS (4.17%) |       FAIL (38.10%) |      PASS (4.17%) | [Nhận xét]              |

*(Số liệu trên lấy từ `data/results/*_metrics.json` và `data/quality/*_quality_report.json` — bạn chỉ cần điền phần "Nhận xét của cá nhân" theo đúng góc nhìn Retrieval Lead của mình.)*

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi].
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi].

Corruption nào ảnh hưởng rõ nhất và vì sao?

[Phân tích dựa trên số liệu.]

Kết quả nào khác với kỳ vọng ban đầu?

[Nêu kết quả, giả thuyết và cách đã kiểm tra.]

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. [Điều học được về data pipeline.]
2. [Điều học được về data quality/observability.]
3. [Điều học được về ảnh hưởng của data đến RAG agent.]

### Nếu có thêm thời gian

[Nêu một cải thiện cụ thể, lý do và cách đo cải thiện đó.]

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** [YYYY-MM-DD]
