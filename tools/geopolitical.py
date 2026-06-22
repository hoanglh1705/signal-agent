async def get_geopolitical_context(sector: str | None) -> dict:
    return {
        "risk_level": "medium",
        "summary": "No immediate geopolitical shock detected.",
        "sector_impact": "limited" if sector else "unknown",
    }
