import tools.news as news_tool
from clients import google_news


async def test_get_news_maps_groq_score(monkeypatch):
    async def fake_search(symbol, since, sector_keywords, limit):
        assert symbol == "VCB"
        return [
            {
                "id": "abc",
                "title": "VCB tăng trần",
                "source": "CafeF",
                "url": "https://example.com/vcb",
                "published_at": "2026-06-20T00:00:00+00:00",
                "impact": 0.8,
                "stance": 0.5,
                "relevance": 0.9,
                "entities": ["VCB", "CTG"],
                "topics": ["banking"],
                "reasons": {
                    "summary": "VCB báo lãi kỷ lục",
                    "confidence": 0.9,
                    "sectors": ["banking"],
                    "symbols": [
                        {"symbol": "VCB", "impact": 0.85, "stance": 0.7},
                        {"symbol": "CTG", "impact": 0.3, "stance": 0.1},
                    ],
                },
            }
        ]

    monkeypatch.setattr(news_tool.article_repo, "search_for_symbol", fake_search)

    items = await news_tool.get_news("VCB", "banking")

    assert len(items) == 1
    it = items[0]
    assert it["summary"] == "VCB báo lãi kỷ lục"
    assert it["confidence"] == 0.9
    assert it["sectors"] == ["banking"]
    assert it["symbol_impact"] == 0.85  # impact riêng cho VCB, không phải CTG
    assert it["impact"] == 0.8


async def test_get_news_summary_falls_back_to_reasoning(monkeypatch):
    """Bài cũ do hệ Go chấm chỉ có 'reasoning'."""

    async def fake_search(symbol, since, sector_keywords, limit):
        return [
            {
                "id": "old",
                "title": "Tin cũ",
                "source": "Go",
                "url": "https://example.com/old",
                "published_at": None,
                "impact": 0.4,
                "stance": 0.0,
                "relevance": None,
                "entities": [],
                "topics": [],
                "reasons": {"reasoning": "Lý do kiểu cũ"},
            }
        ]

    monkeypatch.setattr(news_tool.article_repo, "search_for_symbol", fake_search)

    items = await news_tool.get_news("VCB", "banking")
    assert items[0]["summary"] == "Lý do kiểu cũ"
    assert items[0]["symbol_impact"] is None


async def test_get_news_returns_empty_on_db_error(monkeypatch):
    async def boom(**kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(news_tool.article_repo, "search_for_symbol", boom)

    items = await news_tool.get_news("VCB", "banking")
    assert items == []


def test_google_news_url_encodes_query():
    url = google_news.search_url('"VCB" OR "Vietcombank"')
    assert url.startswith("https://news.google.com/rss/search?q=")
    assert "hl=vi" in url and "ceid=VN:vi" in url
    assert "VCB" in url


def test_symbol_query_with_and_without_name():
    assert google_news.symbol_query("VCB") == '"VCB"'
    assert google_news.symbol_query("VCB", "Vietcombank") == '"VCB" OR "Vietcombank"'


def test_is_google_news_url():
    from ingestion.gnews_resolver import is_google_news_url

    assert is_google_news_url("https://news.google.com/rss/articles/CBMiABC")
    assert not is_google_news_url("https://vnexpress.net/abc.html")
