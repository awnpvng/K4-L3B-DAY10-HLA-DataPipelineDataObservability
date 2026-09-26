# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thị Bảo Trang |
| MSSV | 2A202602580 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | HLA |
| Vai trò chính | C — Retrieval Lead (Embedding & Vector Index) |
| Repository | https://github.com/awnpvng/K4-L3B-DAY10-HLA-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding model | `src/retrieval/embeddings.py`: `_load_model()`, `MiniLMEmbeddings` | Danh sách `text_for_embedding` và câu truy vấn | Vector MiniLM 384 chiều, chuẩn hóa cosine | Hoàn thành |
| Vector document contract | `LocalEmbeddingIndex._build_documents()` | Clean dataframe có đủ schema từ role B | Document ID, content và metadata hợp lệ cho ChromaDB | Hoàn thành |
| ChromaDB indexing | `LocalEmbeddingIndex.build()`, `load()`, `search()` | Documents và vector embeddings | ChromaDB local persist trong `data/chroma/` | Hoàn thành |
| Embedding manifests | `data/embeddings/papers_embeddings*.json` | Trạng thái baseline/corrupted/repaired | Manifest có model, dimension, collection, count và đường dẫn portable | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác minh contract clean dataframe | Role B — Cleaning & Observability | Chốt đủ các cột `paper_id`, `title`, `text_for_embedding`, `published`, authors/categories, summary và URLs trước khi index |
| Hỗ trợ tích hợp ba trạng thái | Role D/E — Evaluation và Corruption/Repair | Mapping manifest sang ba collection độc lập: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Kiểm tra khả năng tái sử dụng index | Pipeline baseline/corruption | Manifest dùng `data/chroma` thay vì đường dẫn tuyệt đối trên máy cá nhân; collection load lại và search được |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tích hợp `sentence-transformers/all-MiniLM-L6-v2` | `src/retrieval/embeddings.py` | Vector 384 chiều, norm bằng 1.0; model được cache để tránh load lặp | Kiểm tra `dimension == 384` và chuẩn L2 của query vector |
| Kiểm tra input trước khi embedding/index | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | Từ chối query rỗng, document rỗng, dataframe rỗng hoặc thiếu cột bắt buộc | Các validation guards trả `ValueError` đúng trường hợp |
| Build baseline vector store | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Collection `papers-baseline` có đúng 24 documents | `collection.count() == 24` và manifest `document_count: 24` |
| Cô lập ba không gian vector | `papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json` | Baseline 24, corrupted 21, repaired 24 documents | Liệt kê collection trực tiếp từ ChromaDB |
| Kiểm tra semantic retrieval | `LocalEmbeddingIndex.search()` | Query về data observability trả paper cùng chủ đề ở vị trí đầu | Search top-k và kiểm tra title/score trả về |

Output tiêu biểu là `data/embeddings/papers_embeddings.json`: backend `chroma`, model `all-MiniLM-L6-v2`, dimension 384, collection `papers-baseline`, 24 documents và `persist_path: data/chroma`. Commit bằng chứng cho phần việc của tôi là `ae640d1` — `feat(retrieval): complete role C vector indexing`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Sau cleaning, pipeline mới chỉ có văn bản và metadata. RAG cần chuyển từng tài liệu sang vector dense có cùng không gian biểu diễn với query, lưu chúng vào vector store và truy xuất top-k ổn định. Ba trạng thái baseline, corrupted và repaired phải được cô lập; nếu dùng chung hoặc ghi đè sai collection thì phép so sánh metrics sẽ không còn đáng tin cậy.

### Cách triển khai

`MiniLMEmbeddings` tải và cache model bằng `lru_cache`, sinh vector đã chuẩn hóa để ChromaDB dùng cosine distance. Hàm embedding kiểm tra chuỗi rỗng và trả vector 384 chiều.

`LocalEmbeddingIndex._build_documents()` kiểm tra schema trước khi chuyển từng row thành document. Mỗi document có:

- `record_id = paper_id::row_index` để các row duplicate trong corruption vẫn có ID Chroma riêng;
- `content = text_for_embedding` để sinh vector;
- metadata dạng scalar gồm DOI, title, ngày xuất bản, authors, categories, summary và URLs.

Khi build, collection cũ cùng tên được xóa rồi tạo lại theo cosine space. Sau khi add, code đối chiếu số vector, dimension và `collection.count()` với số documents. Manifest lưu đường dẫn tương đối `data/chroma`, nhờ đó repository vẫn load được khi clone sang máy khác. Khi load, code kiểm tra backend, embedding model, document count và collection count trước khi cho phép search.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean dataframe có `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url` |
| Output | Chroma collection, embedding manifest và danh sách `SearchResult` có `paper_id`, title, cosine score, content, metadata |
| Module phụ thuộc | `src/ingestion/cleaning.py`, `src/core/config.py`, MiniLM và ChromaDB |
| Module sử dụng output | `src/retrieval/qa.py`, `agent.py`, `src/evaluation/metrics.py`, hai pipeline orchestration |
| Điều kiện lỗi cần xử lý | Thiếu cột, dataframe/document/query rỗng, embedding sai dimension/count, manifest sai model/backend, Chroma count lệch manifest, `top_k <= 0` |

### Cách xác minh

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
.\.venv\Scripts\python.exe script\run_phase1.py

.\.venv\Scripts\python.exe -c "import chromadb; from core.config import load_settings; s=load_settings(); c=chromadb.PersistentClient(path=str(s.paths.chroma_dir)); print(sorted((x.name, x.count()) for x in c.list_collections()))"
```

- **Kết quả mong đợi:** baseline và repaired có 24 documents, corrupted có 21 documents; manifest baseline ghi dimension 384 và dùng đường dẫn tương đối.
- **Kết quả thực tế:** `[('papers-baseline', 24), ('papers-corrupted', 21), ('papers-repaired', 24)]`; baseline reload và semantic search đều thành công.
- **Artifact/log:** `data/chroma/`, `data/embeddings/papers_embeddings*.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Manifest ban đầu lưu đường dẫn Chroma tuyệt đối, ví dụ `C:\Users\...\data\chroma`. Artifact như vậy chỉ load được trên máy đã sinh ra nó và có nguy cơ vi phạm yêu cầu không hardcode đường dẫn local.
- **Các phương án đã cân nhắc:** lưu đường dẫn tuyệt đối để load trực tiếp; bỏ hẳn `persist_path` và luôn lấy từ settings; hoặc lưu đường dẫn tương đối so với project root.
- **Phương án đã chọn:** lưu `data/chroma` trong manifest và resolve lại theo `settings.paths.project_dir` khi load.
- **Lý do:** vẫn giữ manifest tự mô tả nhưng có thể clone và chạy trên máy khác; đồng thời không phụ thuộc username hay ổ đĩa của người tạo artifact.
- **Bằng chứng quyết định phù hợp:** manifest hiện có `persist_path: "data/chroma"`; index load lại thành công và collection count vẫn đúng 24/21/24.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `OSError: sentence-transformers/all-MiniLM-L6-v2 does not appear to have a file named pytorch_model.bin or model.safetensors.`
- **Lệnh hoặc bước tái hiện:** khởi tạo `MiniLMEmbeddings` và chạy `embed_query()` khi cache Hugging Face mới chỉ có metadata, chưa có model weights.
- **Nguyên nhân gốc:** lần tải model đầu tiên bị gián đoạn nên snapshot cache không đầy đủ; tokenizer/config đã có nhưng thiếu file weights.
- **Cách xử lý:** hoàn tất tải `model.safetensors`, sau đó kiểm tra lại ở offline mode để chắc chắn pipeline không còn phụ thuộc vào network trong lúc demo.
- **Cách xác minh sau khi sửa:** model load được từ cache, query embedding có 384 phần tử và norm 1.0; baseline build đủ 24 documents.
- **Điều học được:** cài được package `sentence-transformers` chưa đồng nghĩa model weights đã sẵn sàng. Với demo offline cần warm up model và xác minh cache trước.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được role A parse thành `PaperRecord` và lưu raw lineage. Role B chuẩn hóa thành clean dataframe, tạo `text_for_embedding` và Quality/Freshness signals. Role C sinh MiniLM embeddings, nạp documents cùng metadata vào ChromaDB. Agent/QA dùng query embedding để lấy top-k context trước khi tạo câu trả lời.
2. Mỗi câu trong evaluation set có `ground_truth_doc_ids`. Retrieval được tính hit khi ít nhất một ID đúng xuất hiện trong top-k. Answer quality được đo bằng Token F1 và judge metrics dựa trên câu trả lời tham chiếu.
3. Quality checks phát hiện tính đầy đủ, duy nhất, độ dài và row count. Freshness monitoring tập trung vào độ tuổi dữ liệu: record stale khi `age_days > 180`, dataset fail SLA khi tỷ lệ stale vượt 25%.
4. Dùng cùng test set giữ nguyên câu hỏi và ground truth, nhờ đó thay đổi metrics phản ánh thay đổi dữ liệu/index thay vì thay đổi độ khó của bài kiểm tra.
5. Repair thành công khi dữ liệu được tái tạo từ raw lineage, Quality/Freshness trở lại PASS, collection repaired có 24 documents và các metrics phục hồi so với corrupted state. Bằng chứng nằm trong clean/repaired artifacts, manifest, quality reports và `repaired_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired + optimized | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Corrupted index chỉ còn 21 rows và mất 5 tài liệu mới nhất nên 4/10 câu không còn lấy đúng ground-truth document; rebuild từ raw phục hồi đủ coverage. |
| `mean_token_f1` | 0.8759 | 0.8213 | 1.0000 | Blank summary, noise, title truncation và sai top-1 làm answer overlap giảm; repaired index cùng post-repair reranking đưa top-1 đúng trở lại. |
| `judge_accuracy` | 0.9000 | 0.8000 | 1.0000 | Chất lượng context suy giảm dẫn đến thêm câu trả lời bị judge đánh sai; repaired state khôi phục toàn bộ 10 mẫu. |
| `mean_judge_score` | 4.2000 | 3.8000 | 5.0000 | Điểm judge đi cùng xu hướng của retrieval và answer quality. |
| Quality checks | PASS (7/7) | FAIL (row count 21) | PASS (7/7) | Quality Gate cung cấp tín hiệu sớm rằng corrupted corpus không nên được đưa vào serving index. |
| Freshness status | PASS (4.17%) | FAIL (38.10%) | PASS (4.17%) | Stale-date corruption vượt SLA 25%; rebuild từ raw đưa phân bố tuổi dữ liệu về baseline. |

### Kết luận từ số liệu

1. Drop 5 tài liệu mới nhất kết hợp title/summary/date corruption → Quality Gate FAIL, corrupted collection chỉ còn 21 documents và stale ratio tăng lên 38.10% → retrieval hit rate giảm từ 1.0 xuống 0.6, trong đó nhóm câu hỏi `date` giảm xuống 0.0.
2. Rebuild clean data từ `crossref_records.json` → Quality/Freshness trở lại PASS, collection `papers-repaired` có 24 documents → retrieval hit rate phục hồi 1.0; sau bước reranking tích hợp, Token F1 và judge metrics đạt 1.0/5.0.

Corruption ảnh hưởng trực tiếp nhất đến retrieval là `drop_latest_records`, vì document đã bị xóa thì vector search không thể truy hồi dù query embedding tốt. Noise và title truncation chủ yếu làm sai thứ hạng; blank summary làm giảm chất lượng context/answer; stale date thể hiện rõ nhất ở Freshness SLA và câu hỏi ngày xuất bản.

Kết quả khác kỳ vọng là repaired `mean_token_f1 = 1.0`, cao hơn baseline 0.8759 thay vì chỉ quay lại đúng baseline. Nguyên nhân không phải repair tự tạo thêm thông tin, mà do pipeline tích hợp thêm title reranker trên các semantic candidates sau repair. Báo cáo vì vậy ghi rõ trạng thái `Repaired + optimized` để không quy toàn bộ mức tăng cho repair dữ liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Vector index là một artifact có trạng thái và lineage; phải version hoặc cô lập collection theo từng dataset để đánh giá có ý nghĩa.
2. Data Quality Gate nên chạy trước embedding. Index có thể build thành công về kỹ thuật nhưng vẫn âm thầm chứa dữ liệu thiếu, stale hoặc nhiễu.
3. Retrieval Hit Rate và answer metrics đo hai tầng khác nhau: lấy đúng document chưa chắc tạo đúng câu trả lời, nhưng mất document ground truth thường giới hạn trực tiếp chất lượng downstream.

### Nếu có thêm thời gian

Tôi sẽ bổ sung version/hash của clean dataset và model vào manifest, atomic collection swap, cùng các metrics Retrieval Recall@k, MRR và nDCG. Cải thiện được xem là đạt khi pipeline phát hiện manifest lệch dataset trước serving, rebuild không để lại orphan segment và các metrics top-k được sinh tự động cho cả ba trạng thái.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Bảo Trang

**Ngày xác nhận:** 2026-09-26
