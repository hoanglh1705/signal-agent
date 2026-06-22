"""Giải link redirect của Google News bằng Playwright (headless browser).

Link RSS Google News dạng news.google.com/rss/articles/CBMi... là trang trung
gian, JS sẽ redirect tới bài gốc. httpx + trafilatura không bóc được. Ở đây ta
mở link bằng Chromium headless, đợi rời khỏi news.google.com, lấy HTML đã render
rồi bóc nội dung.

Browser được khởi tạo một lần và tái sử dụng (như http client / db pool).
Nhớ gọi close_browser() lúc shutdown (CLI / FastAPI lifespan).
"""

import logging

import trafilatura
from playwright.async_api import async_playwright

from config import settings

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_playwright = None
_browser = None


async def _get_browser():
    global _playwright, _browser
    if _browser is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser


async def close_browser() -> None:
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


def is_google_news_url(url: str) -> bool:
    return "news.google.com" in url


async def resolve_text(url: str) -> tuple[str, str]:
    """Mở link Google News, trả về (final_url, text). Rỗng nếu thất bại."""
    timeout_ms = settings.gnews_nav_timeout_sec * 1000
    try:
        browser = await _get_browser()
        context = await browser.new_context(user_agent=_USER_AGENT)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Đợi JS redirect rời khỏi news.google.com (bỏ qua nếu không nhảy).
            try:
                await page.wait_for_url(
                    lambda u: "news.google.com" not in u, timeout=timeout_ms
                )
            except Exception:
                pass
            final_url = page.url
            html = await page.content()
        finally:
            await page.close()
            await context.close()
    except Exception:
        logger.warning("Playwright resolve failed: %s", url, exc_info=True)
        return url, ""

    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    return final_url, text.strip()
