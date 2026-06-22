# Module Article (Tin tức) — Tài liệu nghiệp vụ

> Góc nhìn: **Business Analyst**. Tài liệu mô tả *mục tiêu nghiệp vụ, phạm vi,
> luồng xử lý, dữ liệu và quy tắc* của module thu thập tin tức phục vụ sinh tín
> hiệu. Không đi sâu chi tiết code; phần kỹ thuật xem trực tiếp trong `ingestion/`,
> `db/`, `tools/news.py`.

## 1. Bối cảnh & vấn đề

`signal-agent` sinh tín hiệu giao dịch cho từng mã cổ phiếu. Một trong các đầu
vào quan trọng là **tin tức** liên quan tới mã/ngành/thị trường. Trước đây tool
lấy tin (`GetNews`) chỉ trả dữ liệu **giả lập (mock)** → agent không có ngữ cảnh
tin thật để lý giải khuyến nghị BUY/KEEP/SELL.

Module Article giải quyết việc này: **thu thập tin thật từ RSS, bóc nội dung,
chấm điểm bằng LLM, lưu trữ, và cung cấp lại cho agent dưới dạng gọn**.

## 2. Mục tiêu

| # | Mục tiêu nghiệp vụ |
|---|---|
| G1 | Agent có tin tức thật, liên quan tới mã/ngành để lý giải tín hiệu |
| G2 | Mỗi bài tin được Groq AI chấm điểm sẵn (tóm tắt, độ tin cậy, mức tác động, chiều hướng, ngành, impact theo từng mã) để dùng nhanh, rẻ chi phí |
| G3 | Lưu vết đầy đủ phục vụ kiểm tra lại (audit) vì sao hệ thống khuyến nghị một chiều nào đó |
| G4 | Dùng chung kho dữ liệu tin với hệ Go (`signal-engine`) — không phân mảnh dữ liệu |

## 3. Phạm vi

**Trong phạm vi**
- Thu thập tin từ **Google News RSS** (theo mã + theo ngành) và **RSS báo tài chính VN** (VnExpress, CafeF, VnEconomy, Thanh Niên).
- Với tin Google News (link là trang chuyển hướng), **giải về bài gốc bằng trình duyệt headless (Playwright)** rồi mới bóc nội dung.
- Bóc nội dung chính của bài, chuẩn hoá, loại trùng.
- Chấm điểm từng bài bằng **Groq AI**: **summary** (tóm tắt), **confidence** (độ tin cậy), **impact** (mức tác động), **stance** (chiều hướng), **sectors** (ngành bị ảnh hưởng), và **impact theo từng mã** chứng khoán.
- Lưu vào kho dữ liệu dùng chung; cung cấp tool tra cứu tin theo mã + tool lấy toàn văn.

**Ngoài phạm vi (đợt này)**
- Không tự tạo cấu trúc bảng (do hệ Go sở hữu và khởi tạo).
- Không tổng hợp điểm thị trường (daily score) — đó là phần của hệ Go.

## 4. Các bên liên quan (Actors)

| Actor | Vai trò |
|---|---|
| **Signal Agent** | Người tiêu dùng tin: gọi tool lấy tin khi sinh tín hiệu |
| **Ingestion Job** | Tiến trình thu thập tin (chạy định kỳ hoặc theo yêu cầu) |
| **Vận hành (Ops)** | Kích hoạt ingestion qua CLI hoặc API; theo dõi kết quả |
| **Hệ Go `signal-engine`** | Sở hữu kho dữ liệu (bảng tin), cũng ghi/đọc cùng bảng |
| **Groq AI** | Dịch vụ LLM chấm điểm bài tin (tóm tắt, confidence, ngành, impact theo mã) |
| **Headless browser (Playwright)** | Giải link chuyển hướng Google News về bài gốc |

## 5. Thuật ngữ (Glossary)

| Thuật ngữ | Ý nghĩa |
|---|---|
| **Article** | Một bài báo đã thu thập |
| **Summary** | Tóm tắt ngắn (1-3 câu) nội dung bài, do Groq sinh |
| **Confidence** | Độ tin cậy của đánh giá, 0.0 → 1.0 |
| **Impact** | Mức độ tác động tới thị trường, 0.0 (nhiễu) → 1.0 (rất lớn) |
| **Stance** | Chiều hướng, -1.0 (rất tiêu cực) → +1.0 (rất tích cực) |
| **Sectors** | Danh sách ngành bị ảnh hưởng (banking, oil_gas, steel...) |
| **Symbol impact** | Impact riêng cho từng mã chứng khoán được nhắc tới |
| **Entities** | Danh sách mã/ticker được nhắc trong bài (dùng để lọc tin theo mã) |
| **Content hash** | Mã băm nội dung để phát hiện bài trùng |
| **Status** | Trạng thái vòng đời bài tin (xem mục 8) |
| **Lookback** | Số ngày lùi về quá khứ để lấy tin gần đây (mặc định 7) |

## 6. Yêu cầu chức năng

| # | Yêu cầu |
|---|---|
| FR1 | Hệ thống thu thập tin từ danh sách nguồn cấu hình được (Google News + RSS báo VN) |
| FR2 | Có thể thu thập **thêm** tin theo mã và theo ngành chỉ định khi chạy |
| FR3 | Mỗi bài được bóc nội dung chính. Tin Google News được giải về bài gốc bằng headless browser trước khi bóc; nếu vẫn không bóc được toàn văn, vẫn giữ và chấm điểm theo tiêu đề |
| FR4 | Bài trùng nội dung bị đánh dấu **DUPLICATE**, không tính trùng khi tra cứu |
| FR5 | Mỗi bài (không trùng) được **Groq AI** chấm điểm: summary, confidence, impact, stance, sectors (ngành), và impact theo từng mã |
| FR6 | Lưu lại prompt và kết quả chấm điểm để phục vụ audit (G3) |
| FR7 | Agent tra cứu được tin liên quan tới một mã trong cửa sổ lookback, sắp xếp theo mức tác động và độ mới |
| FR8 | Lọc tin theo mã dựa trên **entities chứa mã** *hoặc* **tiêu đề/nội dung chứa mã/từ khoá ngành** |
| FR9 | Có thể lấy toàn văn một bài theo mã định danh khi cần phân tích sâu |
| FR10 | Khi kho dữ liệu lỗi/không có tin, tool trả danh sách rỗng để luồng sinh tín hiệu vẫn chạy (fallback an toàn) |

## 7. Luồng xử lý nghiệp vụ

### 7.1 Luồng thu thập (Ingestion)

```
Nguồn RSS ─▶ Lấy danh sách bài ─▶ Gộp & bỏ trùng URL
        │
        ▼
   Với mỗi bài:
     1. Lưu bài (trạng thái NEW)
     2. Tải & bóc nội dung chính        ─▶ FETCHED
        - Google News: mở bằng headless browser, đợi redirect
          về bài gốc, lấy HTML đã render rồi bóc
        - Báo VN (link trực tiếp): tải HTTP thường rồi bóc
     3. Chuẩn hoá + tính content hash
     4. Trùng nội dung?  ── có ─▶ DUPLICATE (dừng)
                          └ không
     5. Groq AI chấm điểm (summary, confidence, impact,
        stance, sectors, impact theo từng mã)
     6. Lưu điểm + prompt + kết quả     ─▶ SCORED
```

### 7.2 Luồng tiêu thụ (khi sinh tín hiệu)

```
Agent (node load_news) ─▶ GetNews(symbol, sector)
   └─▶ Tra kho: tin trong N ngày gần đây, khớp mã/ngành,
        ưu tiên impact cao + tin mới
   └─▶ Trả bản gọn: tiêu đề, nguồn, link, ngày, tóm tắt,
        confidence, impact, stance, ngành, impact riêng cho mã đang xét
   └─▶ Khi cần đào sâu: GetArticleText(id) lấy toàn văn
```

## 8. Vòng đời trạng thái bài tin

| Trạng thái | Ý nghĩa |
|---|---|
| `NEW` | Vừa ghi nhận từ feed, chưa tải nội dung |
| `FETCHED` | Đã tải & chuẩn hoá nội dung |
| `DUPLICATE` | Trùng nội dung với bài đã có → loại khỏi kết quả tra cứu |
| `SCORED` | Đã chấm điểm xong, sẵn sàng cho agent dùng |
| `ERROR` | Lỗi xử lý (dự phòng) |

> Trạng thái khớp với hệ Go để hai hệ dùng chung một vòng đời.

## 9. Dữ liệu (góc nhìn nghiệp vụ)

Dùng **chung 2 bảng** với hệ Go `signal-engine` (Go sở hữu cấu trúc; Python chỉ đọc/ghi).

**Bảng `articles`** — mỗi dòng là một bài:
- Định danh, **URL (duy nhất)**, nguồn, ngày đăng, ngày thu thập
- Tiêu đề, nội dung, bản chuẩn hoá, mã băm nội dung (duy nhất)
- Trạng thái, prompt chấm điểm, kết quả chấm điểm (audit)

**Bảng `article_scores`** — điểm của mỗi bài (do Groq sinh):
- **impact, stance** — dùng cho xếp hạng & lý giải
- **relevance** — lưu **confidence** (độ tin cậy) để xếp hạng theo cột số
- **entities** — mảng ticker (string), dùng để **lọc tin theo mã**
- **topics** — danh sách **ngành** bị ảnh hưởng
- **reasons** (jsonb) — `{summary, confidence, sectors, symbols:[{symbol, impact, stance}]}` — chứa tóm tắt và **impact theo từng mã**

> Vì dùng chung bảng do Go định nghĩa, các trường mới của Groq được lưu gọn vào
> các cột jsonb sẵn có (`entities`, `topics`, `reasons`) thay vì thêm cột — không
> phá vỡ schema, query "tin theo mã" vẫn chạy do `entities` vẫn là mảng ticker.

## 10. Quy tắc nghiệp vụ (Business Rules)

| # | Quy tắc |
|---|---|
| BR1 | Một URL chỉ tồn tại một bài (chống lặp theo URL) |
| BR2 | Hai bài có cùng nội dung (cùng content hash) coi là trùng → bài sau là `DUPLICATE` |
| BR3 | Tin trả cho agent giới hạn trong **N ngày gần đây** (lookback, mặc định 7) |
| BR4 | Số tin trả mặc định cho mỗi mã là **8** bài, ưu tiên impact cao rồi đến tin mới |
| BR5 | Bài `DUPLICATE` không xuất hiện trong kết quả tra cứu của agent |
| BR6 | Tin Google News được giải về bài gốc qua headless browser để bóc toàn văn; trường hợp vẫn thất bại thì chấm điểm theo **tiêu đề** (tiêu đề Google News giàu thông tin theo mã) |
| BR7 | Lỗi kho dữ liệu không được làm gãy luồng sinh tín hiệu (trả rỗng) |

## 11. Giao diện vận hành & tích hợp

| Kênh | Mô tả |
|---|---|
| **CLI** | `make ingest` (tuỳ chọn `SYMBOLS=...`, `SECTORS=...`) — chạy thu thập một lượt; phù hợp cron |
| **API** | `POST /v1/ingest` với `{symbols, sectors}` — kích hoạt thu thập theo yêu cầu, trả số liệu theo trạng thái |
| **Tool (nội bộ agent)** | `GetNews(symbol, sector)` lấy tin gọn; `GetArticleText(id)` lấy toàn văn |
| **Cấu hình nguồn** | `data/news_sources.yaml` (nguồn cố định) và `data/sector_news_rules.yaml` (từ khoá theo ngành) |

## 12. Cấu hình chính

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `ingest_lookback_days` | 7 | Số ngày lấy tin gần đây |
| `news_default_limit` | 8 | Số tin trả cho agent mỗi mã |
| `ingest_max_concurrency` | 5 | Số bài xử lý song song khi thu thập |
| `gnews_nav_timeout_sec` | 30 | Thời gian chờ tối đa khi giải link Google News bằng browser |
| `groq_model` | `llama-3.3-70b-versatile` | Model Groq dùng để chấm điểm bài tin |
| `groq_api_key` | (env) | API key Groq |
| `postgres_dsn` | DB chung với Go | Kết nối kho dữ liệu tin |

## 13. Hạn chế đã biết & hướng mở rộng

- **Chi phí giải link Google News**: dùng headless browser (Chromium) nên mỗi bài tốn ~1–3s và tài nguyên CPU/RAM; cần cài Chromium trong môi trường chạy. *Hệ quả:* job ingestion nặng hơn, cần đặt lịch và giới hạn song song hợp lý. *Hướng mở rộng:* bổ sung cách giải link bằng HTTP thuần làm phương án nhẹ, dùng browser chỉ khi cần.
- **Phủ tin theo mã**: phụ thuộc tần suất mã xuất hiện trên feed. *Hướng mở rộng:* bổ sung feed Google News riêng cho từng mã theo danh mục.
- **Phụ thuộc lịch chạy ingestion**: agent chỉ thấy tin đã thu thập. Cần đặt lịch chạy phù hợp với khung thời gian giao dịch (horizon).

## 14. Tiêu chí nghiệm thu (Acceptance)

1. Chạy thu thập (CLI/API) tạo được bài mới ở trạng thái `SCORED`, có điểm trong `article_scores`.
2. Gọi sinh tín hiệu cho một mã (vd `VCB`) → có tin thật trong ngữ cảnh; `metadata.news_count > 0`.
3. Bài trùng nội dung được đánh dấu `DUPLICATE` và không lọt vào kết quả tra cứu.
4. Khi kho dữ liệu không sẵn sàng, sinh tín hiệu vẫn chạy (danh sách tin rỗng).
