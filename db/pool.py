"""Async Postgres pool dùng chung cho signal-agent.

Kết nối tới cùng database mà signal-engine (Go) sở hữu. Schema (articles,
article_scores...) do Go quản lý qua gormigrate; Python chỉ đọc/ghi, KHÔNG migrate.
"""

import asyncpg

from config import settings

_pool: asyncpg.Pool | None = None


def _normalize_dsn(dsn: str) -> str:
    """asyncpg chấp nhận postgres:// và postgresql:// nhưng không hiểu query
    param sslmode/connect_timeout kiểu libpq trong vài trường hợp. Ở đây ta chỉ
    chuẩn hoá scheme; phần còn lại asyncpg tự parse."""
    if dsn.startswith("postgres://"):
        return "postgresql://" + dsn[len("postgres://") :]
    return dsn


async def get_pool() -> asyncpg.Pool:
    """Trả pool singleton, lazy-init. Tái sử dụng connection cho mọi query."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=_normalize_dsn(settings.postgres_dsn),
            min_size=1,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    """Đóng pool khi app shutdown (gọi trong FastAPI lifespan)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
