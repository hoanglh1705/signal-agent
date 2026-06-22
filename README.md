`signal-agent` là service/agent chuyên trách việc **thu thập ngữ cảnh thị trường, phân tích bằng LLM, và sinh tín hiệu giao dịch có cấu trúc** cho từng mã cổ phiếu.

Nó không thay thế toàn bộ `signal-engine` Go hiện tại. Go service vẫn là hệ thống chính để quản lý job, database, company list, signal history, UI/API. `signal-agent` chỉ phụ trách phần “reasoning + tool calling + sinh signal”.

**Signal-agent dùng để làm gì**

Đầu vào của `signal-agent` là một request như:

```json
{
  "symbol": "VCB",
  "exchange": "HOSE",
  "sector": "banking",
  "horizon": "T+3",
  "risk_profile": {
    "max_loss_pct": 0.04,
    "risk_per_trade_pct": 0.01,
    "target_rr_t3": 2.0
  }
}
```

Sau đó agent sẽ tự gọi các tool cần thiết, gom dữ liệu, phân tích và trả về tín hiệu:

```json
{
  "symbol": "VCB",
  "trend": "up",
  "action": "BUY",
  "confidence": 0.72,
  "entry_price": 92000,
  "tp_price": 96000,
  "sl_price": 88500,
  "expected_return_t3": 0.043,
  "reason": "..."
}
```

**Các chức năng chính**

1. **Lấy lịch sử giá**

Tool: `GetPriceHistory`

Dùng để lấy OHLCV của mã cổ phiếu trong N phiên gần nhất. Dữ liệu này là nền tảng để đánh giá xu hướng, hỗ trợ/kháng cự, momentum, biến động và vùng vào lệnh.

Ví dụ:
- Giá đóng cửa gần nhất
- Volume
- MA/RSI/ATR nếu có
- Hỗ trợ/kháng cự
- Biến động ngắn hạn

2. **Lấy tin tức theo mã và theo ngành**

Tool: `GetNews`

Dùng để lấy tin liên quan đến:
- Mã cổ phiếu cụ thể, ví dụ `VCB`, `FPT`, `HPG`
- Ngành, ví dụ ngân hàng, chứng khoán, thép, dầu khí, bất động sản
- Thị trường chung

Ví dụ ngành ngân hàng cần quan tâm:
- Lãi suất
- Tỷ giá
- Tăng trưởng tín dụng
- Nợ xấu
- Chính sách Ngân hàng Nhà nước

Ngành dầu khí cần quan tâm:
- Giá dầu
- OPEC
- Căng thẳng Trung Đông
- Nguồn cung năng lượng

3. **Lấy bối cảnh vĩ mô**

Tool: `GetMacroContext`

Dùng để đưa thêm thông tin thị trường chung vào quyết định signal:
- VNIndex confidence
- Tỷ giá USD/VND
- Lãi suất
- US 10Y
- VIX
- DXY/USD index
- Dữ liệu `macro_observations_daily`
- Các score/risk factor đang có trong hệ thống

Mục tiêu là tránh việc agent chỉ nhìn chart cổ phiếu mà bỏ qua bối cảnh thị trường.

4. **Lấy bối cảnh địa chính trị**

Tool: `GetGeopoliticalContext`

Dùng để phát hiện các sự kiện lớn có thể ảnh hưởng tới thị trường, ví dụ:
- Chiến tranh Iran-Mỹ
- Căng thẳng Trung Đông
- Xung đột Nga-Ukraine
- Rủi ro Biển Đỏ / tuyến vận tải
- Chính sách thuế quan Mỹ-Trung
- Biến động giá dầu, vàng, USD

Không phải tin địa chính trị nào cũng ảnh hưởng như nhau. Agent cần đánh giá mức độ liên quan theo ngành.

Ví dụ:
- Căng thẳng Trung Đông ảnh hưởng mạnh hơn tới dầu khí, vận tải, hóa chất.
- Lãi suất Fed và USD mạnh ảnh hưởng mạnh tới ngân hàng, bất động sản, xuất nhập khẩu.
- Chiến tranh thương mại ảnh hưởng mạnh tới xuất khẩu, cảng biển, logistics.

5. **Tổng hợp context trước khi gọi LLM**

Node: `BuildSignalContext`

Agent gom tất cả dữ liệu thành một context sạch:
- Price summary
- Technical summary
- News summary
- Macro summary
- Geopolitical summary
- Sector-specific impact
- Risk profile

Việc này giúp prompt cuối cùng ngắn hơn, ít nhiễu hơn, và dễ audit.

6. **Sinh tín hiệu giao dịch**

Node: `GenerateSignal`

LLM sẽ dựa trên context đã chuẩn hóa để đưa ra:
- `BUY`, `KEEP`, hoặc `SELL`
- Xu hướng
- Độ tin cậy
- Giá vào lệnh
- Take profit
- Stop loss
- Expected return T+3
- Lý do ngắn gọn

7. **Validate kết quả**

Node: `ValidateSignal`

Kiểm tra output trước khi trả về Go service:
- JSON có đúng schema không
- `action` có hợp lệ không
- `confidence` có trong khoảng `0-1` không
- `tp_price`, `sl_price`, `entry_price` có logic không
- Nếu `BUY` nhưng risk/reward xấu thì chuyển về `KEEP` hoặc yêu cầu LLM sửa lại
- Nếu thiếu dữ liệu quan trọng thì fallback an toàn

8. **Lưu thông tin để audit**

Agent nên trả thêm metadata để Go lưu lại:
- Tool nào đã được gọi
- Tin tức nào đã dùng
- Macro/geopolitical context nào ảnh hưởng nhiều nhất
- Raw LLM response
- Final parsed signal
- Validation warnings

Việc này rất quan trọng để sau này kiểm tra lại: vì sao hôm đó hệ thống khuyến nghị `BUY` hoặc `SELL`.

**Tóm lại**

`signal-agent` là “bộ não phân tích” của hệ thống signal.

Nó có nhiệm vụ:
- Lấy dữ liệu giá
- Lấy tin tức
- Lấy macro
- Lấy địa chính trị
- Đánh giá mức độ liên quan theo ngành
- Sinh tín hiệu giao dịch
- Validate output
- Trả JSON sạch cho Go service lưu và hiển thị

Go service vẫn là “xương sống vận hành”, còn `signal-agent` là lớp reasoning chuyên sâu dùng LangGraph/LangChain.