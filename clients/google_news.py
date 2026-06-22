"""Helper build URL Google News RSS search.

Google News có RSS search free, không cần API key:
    https://news.google.com/rss/search?q=<query>&hl=vi&gl=VN&ceid=VN:vi
"""

from urllib.parse import quote_plus

_BASE = "https://news.google.com/rss/search"
_SUFFIX = "hl=vi&gl=VN&ceid=VN:vi"


def search_url(query: str) -> str:
    """Trả URL RSS search cho một query bất kỳ."""
    return f"{_BASE}?q={quote_plus(query)}&{_SUFFIX}"


def symbol_query(symbol: str, company_name: str | None = None) -> str:
    """Query tin theo mã cổ phiếu. Kèm tên công ty nếu có để tăng độ phủ."""
    if company_name:
        return f'"{symbol}" OR "{company_name}"'
    return f'"{symbol}"'
