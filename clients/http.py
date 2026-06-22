import httpx

from config import settings

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Trả về một httpx.AsyncClient dùng chung cho toàn bộ clients.

    Dùng singleton để tái sử dụng connection pool, tránh tạo client mới mỗi
    lần gọi (tốn handshake TLS). Timeout lấy từ settings.
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    """Đóng client khi app shutdown (gọi trong FastAPI lifespan)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
