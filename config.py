import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "signal-agent"
    openapi_api_key: str
    llm_model: str
    request_timeout: int = 20

    # Postgres dùng chung với signal-engine (Go) — đọc/ghi bảng articles, article_scores.
    postgres_dsn: str = "postgresql://tele-money:password123@localhost:5533/tele-money"

    # Ingestion
    ingest_lookback_days: int = 7
    ingest_max_concurrency: int = 5
    ingest_max_body_kb: int = 1024
    news_default_limit: int = 8

    # Groq — dùng để chấm điểm bài tin (tóm tắt, confidence, ngành, impact theo mã)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Google News: link là trang redirect -> dùng headless browser (Playwright)
    # mở link, đợi nhảy về bài gốc rồi bóc nội dung.
    gnews_nav_timeout_sec: int = 30

    # Vietstock
    vietstock_base_url: str = "https://finance.vietstock.vn/data/gettradingresult"
    vietstock_referer: str = "https://finance.vietstock.vn/HCM/thong-ke-giao-dich.htm"
    vietstock_exchange_id: str = "1"
    vietstock_cookie: str | None = None
    vietstock_trading_token: str | None = None

    # LangSmith tracing
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "signal-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    class ConfigDict:
        env_file = ".env"

settings = Settings()


def _configure_langsmith() -> None:
    """Push LangSmith settings into os.environ so LangChain/LangGraph auto-trace.

    pydantic-settings loads .env into this Settings object but not into
    os.environ, which is where LangChain reads its tracing config from.
    """
    if not settings.langsmith_tracing:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key


_configure_langsmith()
