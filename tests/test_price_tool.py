from datetime import datetime, timezone

import pytest

import tools.price as price_tool
from clients.vietstock import StockPrice


def _stock_price(**overrides) -> StockPrice:
    base = dict(
        symbol="HPG",
        date=datetime(2026, 6, 20, tzinfo=timezone.utc),
        price=25.5,
        volume=1_000_000,
        value=9.9e9,
        open=25.0,
        high=26.0,
        low=24.8,
        close=25.5,
        foreign_volume=500,
        buy_foreign_qty=1000,
        buy_foreign_value=25000,
        sell_foreign_qty=1500,
        sell_foreign_value=38000.0,
        owned_ratio=12.3,
        dividend=0,
        yield_=1.1,
        beta=0.9,
        eps=3000.0,
        pe=8.5,
        feps=3200.0,
        bvps=15000.0,
        pb=1.7,
        total_room=100,
        curr_room=40,
        remain_room=60.0,
        change=1.0,
        change_pct=2.04,
    )
    base.update(overrides)
    return StockPrice(**base)


async def test_get_price_history_converts_to_legacy_dict(monkeypatch):
    async def fake_history(symbol, from_date, to_date, page_size):
        return [_stock_price(), _stock_price(close=30.0)]

    monkeypatch.setattr(price_tool._vietstock, "get_stock_price_history", fake_history)

    rows = await price_tool.get_price_history("HPG", days=5)

    assert len(rows) == 2
    first = rows[0]
    # shape cũ mà node/graph đang dùng
    assert set(["date", "open", "high", "low", "close", "volume"]) <= first.keys()
    assert first["date"] == "2026-06-20"
    assert first["close"] == 25.5
    # field mở rộng
    assert first["pe"] == 8.5
    assert first["foreign_volume"] == 500
    assert rows[1]["close"] == 30.0


async def test_get_price_history_falls_back_to_mock_on_error(monkeypatch):
    async def boom(symbol, from_date, to_date, page_size):
        raise RuntimeError("vietstock down")

    monkeypatch.setattr(price_tool._vietstock, "get_stock_price_history", boom)

    rows = await price_tool.get_price_history("HPG", days=7)

    # mock trả đúng số ngày và có shape cơ bản
    assert len(rows) == 7
    assert set(["date", "open", "high", "low", "close", "volume"]) <= rows[0].keys()
