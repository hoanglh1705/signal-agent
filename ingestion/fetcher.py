"""Tải HTML bài báo và bóc nội dung chính bằng trafilatura."""

import logging

import trafilatura

from clients.http import get_client
from config import settings

logger = logging.getLogger(__name__)


async def fetch_text(url: str) -> str:
    """Trả về text nội dung chính của bài. Rỗng nếu fetch/extract thất bại."""
    try:
        resp = await get_client().get(url)
        resp.raise_for_status()
    except Exception:
        logger.warning("fetch failed: %s", url, exc_info=True)
        return ""

    max_bytes = settings.ingest_max_body_kb * 1024
    html = resp.text[:max_bytes] if max_bytes else resp.text

    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    return text.strip()
