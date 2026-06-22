"""Client gọi Vietstock để lấy giá / thống kê giao dịch cổ phiếu.

Lớp này chỉ lo "transport": dựng request,
parse response Vietstock, trả về StockPrice đã chuẩn hoá. Việc chọn provider /
fallback / ghi vào state là việc của tools/ và nodes/.
"""

import re
from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from clients.http import get_client
from config import settings

# Token form (__RequestVerificationToken). Khác với token trong Cookie.
# Override bằng env settings.vietstock_trading_token khi cần.
DEFAULT_TRADING_RESULT_TOKEN = (
    "K2j4JF6t3whFdLqsElKR2Ylzn-la1cZT3d9asV3rqGxTbRS38x3E5ilx0dvlhNEDZWO7igAWyvw0SMgVpAOSiMR8a8JlFOflriTjtkUYA9E1"
)

# Các cột dữ liệu yêu cầu Vietstock trả về.
_COLS = "TKLGD,TGTGD,VHTT,TGG,DC,TGPTG,KLGDKL,GTGDKL"

_DATE_RE = re.compile(r"/Date\((\d+)\)/")


class VietStockTradeData(BaseModel):
    """Một dòng dữ liệu giao dịch thô từ Vietstock.

    Alias khớp json tag của Vietstock. extra="ignore" để bỏ qua hàng chục
    field khác trong response (Price1/2/3, Header, Columns...) mà ta không dùng.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    trading_date: str = Field("", alias="TradingDate")
    last_price: float = Field(0, alias="LastPrice")
    adjust_volume: float = Field(0, alias="AdjustVolume")
    total_val: float = Field(0, alias="TotalVal")
    open_price: float = Field(0, alias="OpenPrice")
    highest_price: float = Field(0, alias="HighestPrice")
    lowest_price: float = Field(0, alias="LowestPrice")
    close_price: float = Field(0, alias="ClosePrice")
    foreign_buy_vol: float = Field(0, alias="ForeignBuyVol")
    foreign_sell_vol: float = Field(0, alias="ForeignSellVol")
    foreign_buy_val: float = Field(0, alias="ForeignBuyVal")
    foreign_sell_val: float = Field(0, alias="ForeignSellVal")
    owned_ratio: float = Field(0, alias="OwnedRatio")
    dividend: float = Field(0, alias="Dividend")
    yield_: float = Field(0, alias="Yield")
    beta: float = Field(0, alias="Beta")
    eps: float = Field(0, alias="EPS")
    pe: float = Field(0, alias="PE")
    feps: float = Field(0, alias="FEPS")
    bvps: float = Field(0, alias="BVPS")
    pb: float = Field(0, alias="PB")
    total_room: float = Field(0, alias="TotalRoom")
    curr_room: float = Field(0, alias="CurrRoom")
    remain_room: float = Field(0, alias="RemainRoom")
    change: float = Field(0, alias="Change")
    per_change: float = Field(0, alias="PerChange")


class VietStockTradeDataResp(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    data: list[VietStockTradeData] = Field(default_factory=list, alias="Data")


class StockPrice(BaseModel):
    """Giá cổ phiếu đã chuẩn hoá"""

    symbol: str
    date: datetime
    price: float
    volume: int
    value: float
    open: float
    high: float
    low: float
    close: float
    foreign_volume: int
    buy_foreign_qty: int
    buy_foreign_value: int
    sell_foreign_qty: int
    sell_foreign_value: float
    owned_ratio: float
    dividend: float
    yield_: float
    beta: float
    eps: float
    pe: float
    feps: float
    bvps: float
    pb: float
    total_room: float
    curr_room: float
    remain_room: float
    change: float
    change_pct: float


def _parse_trading_date(raw: str) -> datetime:
    """Parse chuỗi dạng `/Date(1700000000000)/` (Unix millis) sang datetime."""
    if raw:
        m = _DATE_RE.search(raw)
        if m:
            ms = int(m.group(1))
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


class VietstockClient:
    def __init__(
        self,
        cookie: str | None = None,
        trading_token: str | None = None,
    ) -> None:
        self._cookie = cookie or settings.vietstock_cookie or ""
        self._trading_token = (
            trading_token
            or settings.vietstock_trading_token
            or DEFAULT_TRADING_RESULT_TOKEN
        )

    async def get_stock_price(self, symbol: str) -> StockPrice:
        """Lấy 1 record giá mới nhất."""
        today = date.today()
        rows = await self._fetch(symbol, today, today, page_size=1)
        if not rows:
            raise ValueError(f"no data found for symbol {symbol}")
        return self._map(rows[0], symbol)

    async def get_stock_price_history(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        page_size: int = 10,
    ) -> list[StockPrice]:
        """Lấy lịch sử giá trong khoảng [from_date, to_date]."""
        rows = await self._fetch(symbol, from_date, to_date, page_size=page_size)
        if not rows:
            raise ValueError(f"no data found for symbol {symbol}")
        return [self._map(row, symbol) for row in rows]

    async def _fetch(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        page_size: int,
    ) -> list[VietStockTradeData]:
        form = {
            "Code": symbol,
            "OrderBy": "",
            "OrderDirection": "desc",
            "PageIndex": "1",
            "PageSize": str(page_size),
            "FromDate": from_date.strftime("%Y-%m-%d"),
            "ToDate": to_date.strftime("%Y-%m-%d"),
            "ExportType": "default",
            "Cols": _COLS,
            "ExchangeID": settings.vietstock_exchange_id,
            "__RequestVerificationToken": self._trading_token,
        }

        resp = await get_client().post(
            settings.vietstock_base_url,
            data=form,
            headers=self._headers(),
        )
        resp.raise_for_status()

        # Vietstock trả HTML khi cookie/token hết hạn -> ép kiểm tra JSON.
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype.lower():
            raise ValueError("Vietstock returned non-JSON response (cookie/token expired?)")

        parsed = VietStockTradeDataResp.model_validate(resp.json())
        return parsed.data

    @staticmethod
    def _map(data: VietStockTradeData, symbol: str) -> StockPrice:
        return StockPrice(
            symbol=symbol,
            date=_parse_trading_date(data.trading_date),
            price=data.last_price,
            volume=int(data.adjust_volume),
            value=data.total_val,
            open=data.open_price,
            high=data.highest_price,
            low=data.lowest_price,
            close=data.close_price,
            foreign_volume=int(data.foreign_sell_vol - data.foreign_buy_vol),
            buy_foreign_qty=int(data.foreign_buy_vol),
            buy_foreign_value=int(data.foreign_buy_val),
            sell_foreign_qty=int(data.foreign_sell_vol),
            sell_foreign_value=data.foreign_sell_val,
            owned_ratio=data.owned_ratio,
            dividend=data.dividend,
            yield_=data.yield_,
            beta=data.beta,
            eps=data.eps,
            pe=data.pe,
            feps=data.feps,
            bvps=data.bvps,
            pb=data.pb,
            total_room=data.total_room,
            curr_room=data.curr_room,
            remain_room=data.remain_room,
            change=data.change,
            change_pct=data.per_change,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://finance.vietstock.vn",
            "Pragma": "no-cache",
            "Referer": settings.vietstock_referer,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": self._cookie,
        }
