from state import SignalState

async def build_context(state: SignalState) -> SignalState:
    req = state["request"]
    price_history = state.get("price_history", [])
    latest_price = price_history[-1]["close"] if price_history else None

    context = {
        "symbol": req.symbol,
        "sector": req.sector,
        "horizon": req.horizon,
        "risk_profile": req.risk_profile.model_dump(),
        "latest_price": latest_price,
        "price_history": price_history[-20:],
        "news": state.get("news_items", []),
        "macro": state.get("macro_context", {}),
        "geopolitical": state.get("geopolitical_context", {}),
    }

    return {
        **state,
        "signal_context": context,
    }