async def get_news(symbol: str, sector: str | None) -> list[dict]:
    return [
        {
            "title": f"Market news related to {symbol}",
            "source": "mock",
            "url": "",
            "summary": "No major negative company-specific news detected.",
        }
    ]