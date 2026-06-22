import logging
from datetime import date, timedelta

from clients.vietstock import StockPrice, VietstockClient

logger = logging.getLogger(__name__)

_vietstock = VietstockClient()


async def get_price_history(symbol: str, days: int = 30) -> list[dict]:
    """Lấy lịch sử giá. Ưu tiên Vietstock, lỗi thì fallback về mock.

    Trả list[dict] theo đúng shape cũ (date/open/high/low/close/volume) để
    node và graph không cần đổi, kèm các field mở rộng (pe, eps, foreign...).
    """
    today = date.today()
    try:
        prices = await _vietstock.get_stock_price_history(
            symbol,
            from_date=today - timedelta(days=days),
            to_date=today,
            page_size=days,
        )
        return [_to_dict(p) for p in prices]
    except Exception:
        logger.warning(
            "Vietstock lookup failed for %s, falling back to mock",
            symbol,
            exc_info=True,
        )
        return _mock(symbol, days)


def _to_dict(p: StockPrice) -> dict:
    return {
        "date": p.date.date().isoformat(),
        "open": p.open,
        "high": p.high,
        "low": p.low,
        "close": p.close,
        "volume": p.volume,
        # mở rộng
        "value": p.value,
        "change": p.change,
        "change_pct": p.change_pct,
        "foreign_volume": p.foreign_volume,
        "pe": p.pe,
        "eps": p.eps,
        "pb": p.pb,
    }


def _mock(symbol: str, days: int) -> list[dict]:
    today = date.today()
    return [
        {
            "date": str(today - timedelta(days=i)),
            "open": 100 - i * 0.2,
            "high": 101 - i * 0.2,
            "low": 99 - i * 0.2,
            "close": 100.5 - i * 0.2,
            "volume": 1_000_000 + i * 10_000,
        }
        for i in range(days)
    ][::-1]
