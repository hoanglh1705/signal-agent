"""Chấm điểm bài tin bằng Groq.

Output gồm: tóm tắt, độ tin cậy (confidence), mức tác động thị trường (impact),
chiều hướng (stance), ngành bị ảnh hưởng (sectors) và impact theo từng mã chứng
khoán (symbols[]).

Lưu ý về kho dữ liệu dùng chung với Go: bảng article_scores có cột impact, stance
và 3 cột jsonb (topics, entities, reasons). Ta map:
  - impact, stance        -> cột tương ứng
  - entities              -> mảng ticker dạng string (để query "tin theo mã" chạy được)
  - topics                -> danh sách ngành
  - reasons               -> {summary, confidence, sectors, symbols:[{symbol,impact,stance}]}
"""

import json
import logging

from llm import get_groq_llm

logger = logging.getLogger(__name__)

_MAX_CONTENT = 4000

_PROMPT = """Bạn là chuyên gia phân tích tin tức tài chính thị trường chứng khoán Việt Nam.
Phân tích bài báo sau và trả về DUY NHẤT một JSON (không kèm giải thích ngoài JSON).

Tiêu đề: {title}
Nội dung: {content}

JSON cần có các trường:
- "summary": string — tóm tắt ngắn gọn 1-3 câu bằng tiếng Việt.
- "confidence": number 0.0..1.0 — mức độ tin cậy của đánh giá này (dữ liệu rõ ràng tới đâu).
- "impact": number 0.0..1.0 — mức tác động tới thị trường (1.0 = khủng hoảng/bùng nổ lớn, 0.0 = nhiễu).
- "stance": number -1.0..1.0 — chiều hướng (-1.0 rất tiêu cực, 0.0 trung tính, 1.0 rất tích cực).
- "sectors": array[string] — các ngành bị ảnh hưởng (vd: banking, oil_gas, steel, real_estate, securities).
- "symbols": array các object {{"symbol": string (mã CK, vd VCB), "impact": number 0.0..1.0, "stance": number -1.0..1.0}} — impact riêng cho từng mã được nhắc tới.
"""


def build_prompt(title: str, text: str) -> str:
    return _PROMPT.format(title=title, content=text[:_MAX_CONTENT])


def _parse(raw: str) -> dict:
    """Bóc JSON từ output LLM (chịu được khi bị bọc trong ```json)."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1:
        s = s[start : end + 1]
    return json.loads(s)


def _clamp(v, lo: float, hi: float, default: float = 0.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def _norm_symbols(raw_symbols) -> list[dict]:
    out: list[dict] = []
    for item in raw_symbols or []:
        if isinstance(item, dict):
            sym = str(item.get("symbol", "")).strip().upper()
            if not sym:
                continue
            out.append(
                {
                    "symbol": sym,
                    "impact": _clamp(item.get("impact", 0.0), 0.0, 1.0),
                    "stance": _clamp(item.get("stance", 0.0), -1.0, 1.0),
                }
            )
        elif isinstance(item, str) and item.strip():
            out.append({"symbol": item.strip().upper(), "impact": 0.0, "stance": 0.0})
    return out


def _empty(prompt: str) -> dict:
    return {
        "summary": "",
        "confidence": 0.0,
        "impact": 0.0,
        "stance": 0.0,
        "sectors": [],
        "symbols": [],
        "prompt": prompt,
    }


async def score(title: str, text: str) -> dict:
    """Chấm điểm 1 bài. Fallback an toàn (giá trị 0/rỗng) khi lỗi."""
    prompt = build_prompt(title, text)
    try:
        resp = await get_groq_llm().ainvoke(prompt)
        data = _parse(resp.content if hasattr(resp, "content") else str(resp))
    except Exception:
        logger.warning("Groq score failed for title=%s", title[:60], exc_info=True)
        return _empty(prompt)

    sectors = [str(s).strip() for s in (data.get("sectors") or []) if str(s).strip()]
    return {
        "summary": str(data.get("summary", "")),
        "confidence": _clamp(data.get("confidence", 0.0), 0.0, 1.0),
        "impact": _clamp(data.get("impact", 0.0), 0.0, 1.0),
        "stance": _clamp(data.get("stance", 0.0), -1.0, 1.0),
        "sectors": sectors,
        "symbols": _norm_symbols(data.get("symbols")),
        "prompt": prompt,
    }
