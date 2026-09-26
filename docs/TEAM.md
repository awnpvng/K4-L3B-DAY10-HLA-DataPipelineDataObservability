# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `HLA`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** [github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability](https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability)

---

## # Thành viên

| STT | Họ và tên              | MSSV        | Email                        | Vai trò & Phân công công việc                                                                                                                | Báo cáo cá nhân         |
| --: | ------------------------- | ----------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
|   1 | Trương Hoàng Thành An | 2A202602574 | truonghoangthanhan@gmail.com | **A — Data Lead**: Ingestion & Raw Lineage (`src/ingestion/crossref.py`, `data/raw/*`)                                                 | `report/2A202602574_TruongHoangThanhAn.md` |
|   2 | Nguyễn Thị Bảo Trang   | 2A202602580 | ntbtrang.forwork@gmail.com   | **C — Retrieval Lead**: Embedding & Vector Index (`src/retrieval/embeddings.py`, `src/retrieval/index.py`)                             | `report/2A202602580_NguyenThiBaoTrang.md` |
|   3 | Phan Thị Khánh Linh     | 2A202602310 | luuthiy20111983@gmail.com    | **B — Quality Lead**: Cleaning & Observability (`src/ingestion/cleaning.py`, `src/observability/quality.py`)                           | `report/2A202602310_PhanThiKhanhLinh.md` |
|   4 | Đàm Việt Hưng        | 2A202602600 | hungdam969@gmail.com         | **D — Agent/Eval Lead**: QA Agent & Evaluation (`src/retrieval/agent.py`, `llm.py`, `qa.py`, `src/evaluation/*`)                   | `report/2A202602600_DamVietHung.md` |
|   5 | Nguyễn Hồng Cường     | 2A202602415 | hongcuong0626@gmail.com      | **E — Resilience Lead**: Corruption, Repair & Báo cáo (`src/ingestion/corruption.py`, `script/run_corruption_flow.py`, `report/*`) | `report/2A202602415_NguyenHongCuong.md` |

*(Chi tiết lịch chạy theo từng checkpoint CP0–CP6 và phân công song song xem tại `plan.md` ở thư mục gốc repo)*.

---

## # Cá nhân

### ## Trương Hoàng Thành An - 2A202602574 (Role A — Data Lead)

- **Vai trò:** Phụ trách Ingestion & Raw Data Lineage.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API (`parse_crossref_payload`, `fetch_source_records`, `load_raw_records`) với cơ chế retry (429/503) và Fallback offline trong `src/ingestion/crossref.py`.
  - Bảo toàn 2 raw artifact: `data/raw/crossref_response.json` và `data/raw/crossref_records.json`.
  - Hỗ trợ dựng `.venv` / `.env` chung cho cả nhóm ở Checkpoint 0.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### ## Nguyễn Thị Bảo Trang - 2A202602580 (Role C — Retrieval Lead)

- **Vai trò:** Phụ trách Embedding & Vector Database.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` trong `src/retrieval/embeddings.py`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong `src/retrieval/index.py`.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### ## Phan Thị Khánh Linh - 2A202602310 (Role B — Quality Lead)

- **Vai trò:** Phụ trách Data Cleaning & Data Observability.
- **Công việc chi tiết đã hoàn thành:**
  - Chuẩn hóa schema, khử trùng lặp theo `paper_id`, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thiết lập Quality Gate theo chuẩn **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.

### ## Đàm Việt Hưng - 2A202602600 (Role D — Agent/Eval Lead)

- **Vai trò:** Phụ trách QA Agent & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng QA Agent hỗ trợ đa nhà cung cấp LLM (`mock`, `google`, `openai`, `anthropic`) trong `src/retrieval/agent.py`, `llm.py`, `qa.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn qua 4 nhóm nghiệp vụ trong `src/evaluation/testset.py` và đo lường Hit Rate / Token F1 trong `metrics.py`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết kế router LLM linh hoạt và đo lường chất lượng RAG một cách định lượng.

### ## Nguyễn Hồng Cường - 2A202602415 (Role E — Resilience Lead)

- **Vai trò:** Phụ trách Data Corruption, Repair & Báo cáo.
- **Công việc chi tiết đã hoàn thành:**
  - Triển khai 6 kịch bản làm bẩn dữ liệu và đo lường suy giảm trong `src/ingestion/corruption.py`.
  - Thực thi luồng Idempotent Repair và xuất báo cáo đối chiếu 3 trạng thái (Baseline vs Corrupted vs Repaired) qua `script/run_corruption_flow.py` và `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Repair và cách chứng minh định lượng khả năng tự phục hồi của pipeline.
