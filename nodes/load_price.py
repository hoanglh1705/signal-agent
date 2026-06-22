from state import SignalState
from tools.price import get_price_history


async def load_price(state: SignalState) -> SignalState:
    req = state["request"]
    price_history = await get_price_history(req.symbol)

    return {
        **state,
        "price_history": price_history,
    }
