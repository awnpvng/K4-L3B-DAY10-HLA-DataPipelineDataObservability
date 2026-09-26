# PLAN.md — Phân Công Nhóm 5 Người: Day 10 Data Pipeline & Data Observability

> Tổng thời lượng: 240 phút (4 giờ), bám theo `docs/CHECKPOINTS.md` (CP0–CP6) và `docs/RUBRIC.md` (100đ + 10đ bonus).
> Nguyên tắc: pipeline chạy tuần tự (raw → clean → index → agent → eval → corrupt → repair) nên chia theo **module cố định** cho từng người, kết hợp làm song song ở những bước không phụ thuộc nhau, để tối ưu thời gian và đảm bảo 100% thành viên có commit thật trên `main`.

---

## 1. Phân vai theo module (giữ xuyên suốt buổi)

| Người | Vai trò | Module / File phụ trách | Tiêu chí Rubric liên quan |
|---|---|---|---|
| **A — Data Lead** | Ingestion & Raw Lineage | `src/ingestion/crossref.py`, `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | #2 (15đ) |
| **B — Quality Lead** | Cleaning & Observability | `src/ingestion/cleaning.py`, `src/observability/quality.py` | #3 (15đ), #7 (15đ) |
| **C — Retrieval Lead** | Embedding & Vector Index | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | #4 (10đ) |
| **D — Agent/Eval Lead** | QA Agent & Evaluation | `src/retrieval/agent.py`, `llm.py`, `qa.py`, `src/evaluation/testset.py`, `metrics.py` | #5 (10đ), #6 (10đ) |
| **E — Resilience Lead** | Corruption, Repair & Báo cáo | `src/ingestion/corruption.py`, `script/run_corruption_flow.py`, `report/*`, `docs/TEAM.md` | #8 (15đ) |

Tiêu chí #1 (Cấu trúc dự án & môi trường, 10đ) là trách nhiệm chung — cả nhóm đảm bảo `.venv`/`pyproject.toml` chạy được trên máy mỗi người trước khi bắt đầu.

---

## 2. Lịch chạy theo Checkpoint

| CP | Thời gian | Người thực hiện chính | Việc làm song song |
|---|---|---|---|
| **CP0** | 0'–30' | **A**: dựng `.venv`, `.env`, hoàn thiện `crossref.py` + fallback offline | B/C/D/E verify môi trường máy mình (`import chromadb, great_expectations, sentence_transformers` chạy OK) |
| **CP1** | 30'–65' | **B**: `cleaning.py` (age_days, text_for_embedding) + `quality.py` (GX 1.x, Freshness SLA) | **C** viết trước khung `embeddings.py`/`index.py` dựa trên schema cột đã thống nhất |
| **CP2** | 65'–95' | **C**: hoàn thiện ChromaDB indexing trên data sạch của B | **D** viết `testset.py` (không phụ thuộc index, chỉ cần data sạch) |
| **CP3** | 95'–120' | **D**: nối `agent.py`/`llm.py`/`qa.py`, chạy `script/run_phase1.py` | **E** dựng sẵn khung 6 kịch bản trong `corruption.py` |
| **CP4** | 120'–165' | **E**: tiêm lỗi, đo suy giảm (`corruption_log.json`, `corrupted_metrics.json`) | **A** hỗ trợ debug lineage nếu ảnh hưởng raw; **D** hỗ trợ đo metric |
| **CP5** | 165'–210' | **E**: repair + `corruption_report.md` (3 trạng thái) | **B/C** review lại GX & vector index phục hồi đúng chưa |
| **CP6** | 210'–240' | Cả 5 người demo trên bảng | A: ingestion · B: GX/Freshness · C: vector store · D: Agent + Q&A kỹ thuật · E: bảng so sánh 3 trạng thái |

---

## 3. Checklist tránh bị trừ điểm (theo mục 3 `RUBRIC.md`)

- [ ] Mỗi người tự commit trực tiếp phần việc của mình (không commit hộ) → đủ 100% Contributors trên `main`.
- [ ] Mỗi người tự viết phần mình trong `docs/TEAM.md` (thiếu tự khai báo: **-5đ/người**).
- [ ] Không hardcode đường dẫn tuyệt đối (`D:\...`, `C:\Users\...`) trong code, đặc biệt ở `llm.py`/`qa.py` (**-5đ**).
- [ ] Dùng đúng cú pháp Great Expectations 1.x, không dùng cú pháp cũ (**-10đ** nếu sai).
- [ ] Không commit API key/secret vào Git (**-20đ**, hoặc 0đ nếu repo public).
- [ ] Số liệu trong báo cáo phải khớp với kết quả chạy thực tế, không bịa (**-20đ**).
- [ ] Đủ 4 file quy ước: `TEAM.md`, `SUBMISSION.md`, `CHECKPOINTS.md`, và báo cáo cá nhân (**-5đ/file thiếu**).

---

## 4. Gợi ý điểm Bonus (+10đ, chỉ xét khi bài bắt buộc ≥ 85đ)

| Bonus | Người phù hợp | Lý do |
|---|---|---|
| **B1** Dashboard trực quan (+5) | **C** | Đã nắm rõ ChromaDB + data quality, dễ mở rộng UI hiển thị. |
| **B2** Auto-repair pipeline (+5) | **E** | Đã làm corruption/repair, chỉ cần tự động hoá thêm bước phát hiện lỗi → kích hoạt repair. |
| **B3** Pytest CI end-to-end (+5) | **D** hoặc **A** | Đã hiểu rõ luồng end-to-end (`run_phase1.py`), phù hợp viết test bao phủ toàn pipeline. |

Chỉ nên làm bonus sau khi CP0–CP5 đã ổn định và có buffer thời gian ở CP6.
