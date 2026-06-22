"""Tool lấy full text bài báo theo id (dùng khi cần đào sâu)."""

import logging

from db import article_repo

logger = logging.getLogger(__name__)


async def get_article_text(article_id: str) -> str:
    """Trả full text của bài. Rỗng nếu không có / lỗi."""
    try:
        return await article_repo.get_article_text(article_id) or ""
    except Exception:
        logger.warning("get_article_text failed for %s", article_id, exc_info=True)
        return ""
