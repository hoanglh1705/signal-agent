"""Tool lấy tin cho agent: đọc từ bảng articles/article_scores (dùng chung với Go).

Trả về bản gọn (đã được LLM chấm điểm sẵn lúc ingest) để prompt rẻ token.
Full text lấy on-demand qua tools/article.get_article_text.
"""

import logging
from datetime import datetime, timedelta, timezone

from config import settings
from db import article_repo
from ingestion import sources

logger = logging.getLogger(__name__)


async def get_news(symbol: str, sector: str | None) -> list[dict]:
    """Lấy tin liên quan tới mã + ngành trong cửa sổ lookback gần đây.

    Lỗi DB -> trả list rỗng để graph vẫn chạy (fallback an toàn).
    """
    since = datetime.now(timezone.utc) - timedelta(days=settings.ingest_lookback_days)
    try:
        rows = await article_repo.search_for_symbol(
            symbol=symbol,
            since=since,
            sector_keywords=sources.sector_keywords(sector),
            limit=settings.news_default_limit,
        )
    except Exception:
        logger.warning("get_news DB lookup failed for %s", symbol, exc_info=True)
        return []

    return [_to_news_item(r, symbol) for r in rows]


def _symbol_impact(reasons: dict, symbol: str) -> float | None:
    """Impact riêng cho mã đang xét (nếu bài có chấm theo từng mã)."""
    target = symbol.strip().upper()
    for s in reasons.get("symbols") or []:
        if str(s.get("symbol", "")).strip().upper() == target:
            return s.get("impact")
    return None


def _to_news_item(r: dict, symbol: str) -> dict:
    reasons = r.get("reasons") or {}
    # summary do Groq sinh; fallback "reasoning" cho bài cũ do hệ Go chấm.
    summary = reasons.get("summary") or reasons.get("reasoning", "")
    return {
        "id": r["id"],
        "title": r["title"],
        "source": r["source"],
        "url": r["url"],
        "published_at": r["published_at"],
        "summary": summary,
        "impact": r["impact"],
        "stance": r["stance"],
        "confidence": reasons.get("confidence", r.get("relevance")),
        "sectors": reasons.get("sectors") or r.get("topics", []),
        "symbol_impact": _symbol_impact(reasons, symbol),
        "entities": r.get("entities", []),
    }
