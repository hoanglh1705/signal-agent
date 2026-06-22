"""Orchestrate ingestion: RSS -> fetch -> normalize -> dedup -> score -> store.

Tách hẳn khỏi signal graph. Ghi vào bảng articles/article_scores dùng chung với Go.
Trạng thái: NEW -> FETCHED -> SCORED (hoặc DUPLICATE / ERROR).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from clients.http import get_client
from config import settings
from db import article_repo
from db.models import ArticleStatus
from ingestion import dedup, fetcher, gnews_resolver, scorer, sources
from ingestion.normalize import normalize
from ingestion.rss import FeedItem, parse_feed

logger = logging.getLogger(__name__)


async def _fetch_feed(src: sources.Source) -> list[FeedItem]:
    try:
        resp = await get_client().get(src.url)
        resp.raise_for_status()
        return parse_feed(resp.content, src.name)
    except Exception:
        logger.warning("feed fetch failed: %s (%s)", src.name, src.url, exc_info=True)
        return []


async def _collect_items(srcs: list[sources.Source]) -> list[FeedItem]:
    """Parse mọi feed, gộp và bỏ trùng URL."""
    results = await asyncio.gather(*(_fetch_feed(s) for s in srcs))
    seen: set[str] = set()
    items: list[FeedItem] = []
    for feed in results:
        for it in feed:
            if it.url in seen:
                continue
            seen.add(it.url)
            items.append(it)
    return items


async def _process_item(item: FeedItem, run_id: str, sem: asyncio.Semaphore) -> str:
    """Xử lý 1 bài, trả về status cuối (để đếm)."""
    async with sem:
        article_id = await article_repo.upsert_article(
            url=item.url,
            title=item.title,
            source=item.source,
            published_at=item.published_at,
            status=ArticleStatus.NEW,
        )

        # Google News là link redirect -> dùng Playwright giải về bài gốc rồi
        # bóc nội dung. Nguồn RSS báo VN là link trực tiếp -> fetch httpx thường.
        if gnews_resolver.is_google_news_url(item.url):
            _, text = await gnews_resolver.resolve_text(item.url)
        else:
            text = await fetcher.fetch_text(item.url)
        now = datetime.now(timezone.utc)

        # Nếu vẫn không bóc được full text, giữ bài và chấm điểm theo title.
        # Dedup theo text nếu có, ngược lại theo title.
        title_norm, text_norm = normalize(item.title, text)
        chash = dedup.content_hash(text_norm or title_norm)

        if await article_repo.exists_by_content_hash(chash, exclude_id=article_id):
            await article_repo.update_article(
                article_id,
                {
                    "text": text,
                    "title_norm": title_norm,
                    "text_norm": text_norm,
                    "content_hash": chash,
                    "fetched_at": now,
                    "status": ArticleStatus.DUPLICATE,
                },
            )
            return ArticleStatus.DUPLICATE

        await article_repo.update_article(
            article_id,
            {
                "text": text,
                "title_norm": title_norm,
                "text_norm": text_norm,
                "content_hash": chash,
                "fetched_at": now,
                "status": ArticleStatus.FETCHED,
            },
        )

        result = await scorer.score(item.title, text)
        symbols_scored = result["symbols"]
        entities = [s["symbol"] for s in symbols_scored]
        await article_repo.upsert_score(
            article_id=article_id,
            run_id=run_id,
            impact=result["impact"],
            stance=result["stance"],
            relevance=result["confidence"],
            entities=entities,
            topics=result["sectors"],
            reasons={
                "summary": result["summary"],
                "confidence": result["confidence"],
                "sectors": result["sectors"],
                "symbols": symbols_scored,
            },
        )
        await article_repo.update_article(
            article_id,
            {
                "scoring_prompt": result["prompt"],
                "scoring_result": json.dumps(result, ensure_ascii=False),
                "status": ArticleStatus.SCORED,
            },
        )
        return ArticleStatus.SCORED


async def run_once(
    symbols: list[str] | None = None,
    sectors: list[str] | None = None,
) -> dict:
    """Chạy 1 lượt ingestion. Trả về dict counts theo status."""
    if not await article_repo.table_exists():
        raise RuntimeError(
            "Bảng 'articles' chưa tồn tại. Hãy chạy migration của signal-engine (Go) trước."
        )

    srcs = sources.load_static_sources()
    for sector in sectors or []:
        srcs += sources.sector_sources(sector)
    for symbol in symbols or []:
        srcs += sources.symbol_sources(symbol)

    items = await _collect_items(srcs)
    logger.info("collected %d unique items from %d sources", len(items), len(srcs))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    sem = asyncio.Semaphore(settings.ingest_max_concurrency)
    statuses = await asyncio.gather(*(_process_item(it, run_id, sem) for it in items))

    counts: dict[str, int] = {"total": len(statuses)}
    for st in statuses:
        counts[st] = counts.get(st, 0) + 1
    logger.info("ingestion done: %s", counts)
    return counts
