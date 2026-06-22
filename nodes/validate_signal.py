from state import  SignalState

async def validate_signal(state: SignalState) -> SignalState:
    signal = state.get("signal", {})
    req = state["request"]

    errors: list[str] = []

    action = signal.get("action")
    confidence = signal.get("confidence")

    if action not in ["BUY", "KEEP", "SELL"]:
        errors.append(f"Action {action} not supported")

    if not isinstance(confidence, int | float) or confidence < 0 or confidence > 1:
        errors.append(f"Confidence {confidence} not in [0, 1]")

    if action == "BUY":
        entry = signal.get("entry_price")
        tp = signal.get("tp_price")
        sl = signal.get("sl_price")

        if not entry or not tp or not sl:
            errors.append("missing_buy_prices")
        elif sl >= entry or tp <= entry:
            errors.append("invalid_buy_prices")

    if errors:
        signal = {
            "symbol": req.symbol,
            "trend": "sideway",
            "action": "KEEP",
            "confidence": 0.3,
            "entry_price": None,
            "tp_price": None,
            "sl_price": None,
            "expected_return_t3": None,
            "expected_price_t3": None,
            "reason": f"Fallback to KEEP due to validation errors: {', '.join(errors)}",
        }

    return {
        **state,
        "signal": signal,
        "validation_errors": errors,
    }


