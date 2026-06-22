"""Repository cho bảng articles / article_scores (Postgres dùng chung với Go).

Dùng raw SQL qua asyncpg để khớp chính xác schema gorm. asyncpg dùng placeholder
$1, $2... và trả về asyncpg.Record (dict-like).
"""

import json
from datetime import datetime
from typing import Any

from db.models import ArticleStatus
from db.pool import get_pool


async def table_exists() -> bool:
    """Health-check: bảng articles có tồn tại không (Go đã migrate chưa)."""
    pool = await get_pool()
    return bool(
        await pool.fetchval("SELECT to_regclass('public.articles') IS NOT NULL")
    )


async def upsert_article(
    url: str,
    title: str,
    source: str,
    published_at: datetime | None,
    status: str = ArticleStatus.NEW,
) -> str:
    """Insert/giữ article theo url (mirror UpsertByURL của Go). Trả về id.

    id để DB tự sinh (gen_random_uuid). COALESCE giữ giá trị cũ khi conflict.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO articles (url, title, source, published_at, status)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (url) DO UPDATE SET
            title = COALESCE(NULLIF(articles.title, ''), EXCLUDED.title),
            source = COALESCE(NULLIF(articles.source, ''), EXCLUDED.source),
            published_at = COALESCE(articles.published_at, EXCLUDED.published_at)
        RETURNING id
        """,
        url,
        title,
        source,
        published_at,
        status,
    )
    return str(row["id"])


async def update_article(article_id: str, fields: dict[str, Any]) -> None:
    """Update động theo dict {column: value}."""
    if not fields:
        return
    pool = await get_pool()
    cols = list(fields.keys())
    set_clause = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(cols))
    values = [fields[col] for col in cols]
    await pool.execute(
        f"UPDATE articles SET {set_clause} WHERE id = $1",
        article_id,
        *values,
    )


async def exists_by_content_hash(content_hash: str, exclude_id: str = "") -> bool:
    pool = await get_pool()
    if exclude_id:
        val = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM articles WHERE content_hash = $1 AND id <> $2)",
            content_hash,
            exclude_id,
        )
    else:
        val = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM articles WHERE content_hash = $1)",
            content_hash,
        )
    return bool(val)


async def upsert_score(
    article_id: str,
    run_id: str,
    impact: float,
    stance: float,
    entities: list[str],
    reasons: dict[str, Any],
    topics: list[Any] | None = None,
    relevance: float = 0.0,
) -> None:
    """Insert/update score cho 1 article (article_id là PK).

    - entities: mảng ticker (string) để query tin theo mã.
    - topics: danh sách ngành.
    - relevance: dùng lưu confidence để có thể xếp hạng theo cột số.
    """
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO article_scores
            (article_id, run_id, impact, stance, relevance, entities, topics, reasons)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb)
        ON CONFLICT (article_id) DO UPDATE SET
            run_id = EXCLUDED.run_id,
            impact = EXCLUDED.impact,
            stance = EXCLUDED.stance,
            relevance = EXCLUDED.relevance,
            entities = EXCLUDED.entities,
            topics = EXCLUDED.topics,
            reasons = EXCLUDED.reasons
        """,
        article_id,
        run_id,
        impact,
        stance,
        relevance,
        json.dumps(entities, ensure_ascii=False),
        json.dumps(topics or [], ensure_ascii=False),
        json.dumps(reasons, ensure_ascii=False),
    )


async def search_for_symbol(
    symbol: str,
    since: datetime,
    sector_keywords: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Lấy tin liên quan tới 1 mã: entities chứa ticker, hoặc title/text khớp
    mã/tên/keyword ngành. Ưu tiên impact cao và tin mới."""
    pool = await get_pool()

    like_terms = [symbol]
    if sector_keywords:
        like_terms.extend(sector_keywords)
    # $1 symbol (entities), $2 since, $3.. like terms
    like_clauses = []
    params: list[Any] = [symbol, since]
    for term in like_terms:
        params.append(f"%{term}%")
        idx = len(params)
        like_clauses.append(f"a.title ILIKE ${idx} OR a.text_norm ILIKE ${idx}")
    like_sql = " OR ".join(like_clauses)

    params.append(limit)
    limit_idx = len(params)

    rows = await pool.fetch(
        f"""
        SELECT a.id, a.url, a.title, a.source, a.published_at,
               s.impact, s.stance, s.relevance, s.entities, s.topics, s.reasons
        FROM articles a
        LEFT JOIN article_scores s ON s.article_id = a.id
        WHERE a.published_at >= $2
          AND a.status <> 'DUPLICATE'
          AND (
              s.entities @> to_jsonb(ARRAY[$1]::text[])
              OR {like_sql}
          )
        ORDER BY s.impact DESC NULLS LAST, a.published_at DESC
        LIMIT ${limit_idx}
        """,
        *params,
    )
    return [_row_to_dict(r) for r in rows]


async def get_article_text(article_id: str) -> str | None:
    pool = await get_pool()
    return await pool.fetchval("SELECT text FROM articles WHERE id = $1", article_id)


def _json_field(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _row_to_dict(r: Any) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "url": r["url"],
        "title": r["title"],
        "source": r["source"],
        "published_at": r["published_at"].isoformat() if r["published_at"] else None,
        "impact": float(r["impact"]) if r["impact"] is not None else None,
        "stance": float(r["stance"]) if r["stance"] is not None else None,
        "relevance": float(r["relevance"]) if r["relevance"] is not None else None,
        "entities": _json_field(r["entities"]) or [],
        "topics": _json_field(r["topics"]) or [],
        "reasons": _json_field(r["reasons"]) or {},
    }
