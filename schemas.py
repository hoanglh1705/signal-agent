from typing import Any, Literal
from pydantic import BaseModel, Field


class RiskProfile(BaseModel):
    max_loss_pct: float = 0.04
    risk_per_trade_pct: float = 0.01
    target_rr_t3: float = 2.0
    target_return_t3_pct: float | None = 0.05


class SignalRequest(BaseModel):
    symbol: str
    exchange: str | None = None
    sector: str | None = None
    horizon: str = "T+3"
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)


class SignalResponse(BaseModel):
    symbol: str
    trend: Literal["up", "down", "sideway"]
    action: Literal["BUY", "KEEP", "SELL"]
    confidence: float
    entry_price: float | None = None
    tp_price: float | None = None
    sl_price: float | None = None
    expected_return_t3: float | None = None
    expected_price_t3: float | None = None
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)