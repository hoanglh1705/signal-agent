"""Load danh sách nguồn tin từ data/news_sources.yaml + sinh feed theo mã/ngành.

- Nguồn cố định (Google News chung, RSS báo VN) đọc từ news_sources.yaml.
- Feed theo ngành: lấy query trong sector_news_rules.yaml -> Google News search.
- Feed theo mã: build Google News search từ symbol.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from clients import google_news

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SOURCES_FILE = _DATA_DIR / "news_sources.yaml"
# Lưu ý: file rules hiện có khoảng trắng cuối tên.
_SECTOR_RULES_CANDIDATES = [
    _DATA_DIR / "sector_news_rules.yaml",
    _DATA_DIR / "sector_news_rules.yaml ",
]


@dataclass
class Source:
    name: str
    type: str  # "googlenews" | "rss"
    url: str
    trust: float = 1.0


def load_static_sources() -> list[Source]:
    """Nguồn cố định trong news_sources.yaml."""
    if not _SOURCES_FILE.exists():
        return []
    data = yaml.safe_load(_SOURCES_FILE.read_text(encoding="utf-8")) or {}
    out: list[Source] = []
    for item in data.get("sources", []):
        out.append(
            Source(
                name=item["name"],
                type=item.get("type", "rss"),
                url=item["url"],
                trust=float(item.get("trust", 1.0)),
            )
        )
    return out


def _load_sector_rules() -> dict:
    for path in _SECTOR_RULES_CANDIDATES:
        if path.exists():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def sector_queries(sector: str) -> list[str]:
    """Các query Google News cho 1 ngành (từ sector_news_rules.yaml)."""
    rules = _load_sector_rules()
    return list((rules.get(sector) or {}).get("queries", []))


def sector_keywords(sector: str | None) -> list[str]:
    """Keyword để lọc title/text theo ngành (chính là các query rule)."""
    if not sector:
        return []
    return sector_queries(sector)


def sector_sources(sector: str) -> list[Source]:
    return [
        Source(
            name=f"GoogleNews:{sector}",
            type="googlenews",
            url=google_news.search_url(q),
            trust=1.0,
        )
        for q in sector_queries(sector)
    ]


def symbol_sources(symbol: str, company_name: str | None = None) -> list[Source]:
    q = google_news.symbol_query(symbol, company_name)
    return [
        Source(
            name=f"GoogleNews:{symbol}",
            type="googlenews",
            url=google_news.search_url(q),
            trust=1.0,
        )
    ]
