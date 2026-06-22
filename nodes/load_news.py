from state import SignalState
from tools.news import get_news

async def load_news(state: SignalState) -> SignalState:
    req = state["request"]

    news = await get_news(req.symbol, req.sector)
    return {
        **state,
        "news_items": news
    }
