from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from clients.vietstock import VietstockClient


def _row(**overrides) -> dict:
    """Một dòng Data tối thiểu giống Vietstock, cho phép override field."""
    row = {
        "TradingDate": "/Date(1700000000000)/",
        "LastPrice": 25.5,
        "AdjustVolume": 1234567.0,
        "TotalVal": 9.9e9,
        "OpenPrice": 25.0,
        "HighestPrice": 26.0,
        "LowestPrice": 24.8,
        "ClosePrice": 25.5,
        "ForeignBuyVol": 1000,
        "ForeignSellVol": 1500,
        "ForeignBuyVal": 25000,
        "ForeignSellVal": 38000,
        "OwnedRatio": 12.3,
        "Dividend": 0,
        "Yield": 1.1,
        "Beta": 0.9,
        "EPS": 3000.0,
        "PE": 8.5,
        "FEPS": 3200.0,
        "BVPS": 15000.0,
        "PB": 1.7,
        "TotalRoom": 100,
        "CurrRoom": 40,
        "RemainRoom": 60.0,
        "Change": 1,
        "PerChange": 2.04,
        # field thừa, phải bị bỏ qua nhờ extra="ignore"
        "Price1": 99,
        "ColorId": 3,
    }
    row.update(overrides)
    return row


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def patch_http(monkeypatch):
    """Trả về 1 hàm: nhận handler -> patch get_client để VietstockClient dùng mock.

    Bắt lại request cuối qua list `captured` để assert payload/headers.
    """
    captured: list[httpx.Request] = []

    def install(handler):
        def wrapped(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return handler(request)

        client = _mock_client(wrapped)
        monkeypatch.setattr("clients.vietstock.get_client", lambda: client)
        return captured

    return install


def _json_response(rows: list[dict]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"Header": [], "Columns": [], "Rows": len(rows), "Data": rows},
        headers={"content-type": "application/json; charset=utf-8"},
    )


async def test_get_stock_price_history_maps_fields(patch_http):
    captured = patch_http(lambda req: _json_response([_row(), _row(LastPrice=30.0)]))

    client = VietstockClient(cookie="ck=1", trading_token="tok123")
    prices = await client.get_stock_price_history(
        "HPG", from_date=date(2026, 6, 1), to_date=date(2026, 6, 22), page_size=10
    )

    assert len(prices) == 2
    p = prices[0]
    assert p.symbol == "HPG"
    assert p.date.date() == date(2023, 11, 14)  # /Date(1700000000000)/
    assert p.close == 25.5
    assert p.foreign_volume == 500  # sell(1500) - buy(1000)
    assert p.buy_foreign_qty == 1000
    assert p.pe == 8.5
    assert p.change_pct == 2.04
    assert prices[1].price == 30.0

    # request gửi đi đúng form + header
    req = captured[-1]
    assert req.method == "POST"
    assert str(req.url) == "https://finance.vietstock.vn/data/gettradingresult"
    form = parse_qs(req.content.decode())
    assert form["Code"] == ["HPG"]
    assert form["PageSize"] == ["10"]
    assert form["FromDate"] == ["2026-06-01"]
    assert form["ToDate"] == ["2026-06-22"]
    assert form["__RequestVerificationToken"] == ["tok123"]
    assert req.headers["Cookie"] == "ck=1"
    assert req.headers["X-Requested-With"] == "XMLHttpRequest"


async def test_get_stock_price_returns_latest_single(patch_http):
    captured = patch_http(lambda req: _json_response([_row(LastPrice=42.0)]))

    client = VietstockClient(cookie="ck=1", trading_token="tok")
    price = await client.get_stock_price("VNM")

    assert price.symbol == "VNM"
    assert price.price == 42.0
    # get_stock_price chỉ lấy 1 record
    form = parse_qs(captured[-1].content.decode())
    assert form["PageSize"] == ["1"]


async def test_non_json_response_raises(patch_http):
    patch_http(
        lambda req: httpx.Response(
            200, text="<html>login</html>", headers={"content-type": "text/html"}
        )
    )

    client = VietstockClient(cookie="ck=1", trading_token="tok")
    with pytest.raises(ValueError, match="non-JSON"):
        await client.get_stock_price("HPG")


async def test_empty_data_raises(patch_http):
    patch_http(lambda req: _json_response([]))

    client = VietstockClient(cookie="ck=1", trading_token="tok")
    with pytest.raises(ValueError, match="no data found"):
        await client.get_stock_price("HPG")


async def test_http_error_propagates(patch_http):
    patch_http(lambda req: httpx.Response(500, text="boom"))

    client = VietstockClient(cookie="ck=1", trading_token="tok")
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_stock_price("HPG")
