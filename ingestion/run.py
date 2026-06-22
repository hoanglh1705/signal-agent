"""CLI chạy ingestion một lượt (cho cron / chạy tay).

Ví dụ:
    uv run python -m ingestion.run
    uv run python -m ingestion.run --symbols VCB,FPT --sectors banking,oil_gas
"""

import argparse
import asyncio
import logging

from clients.http import close_client
from db.pool import close_pool
from ingestion import pipeline
from ingestion.gnews_resolver import close_browser


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run news ingestion once")
    p.add_argument(
        "--symbols", default="", help="Danh sách mã, phân tách bằng dấu phẩy"
    )
    p.add_argument(
        "--sectors", default="", help="Danh sách ngành, phân tách bằng dấu phẩy"
    )
    return p.parse_args()


def _split(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


async def _main() -> None:
    args = _parse_args()
    try:
        counts = await pipeline.run_once(
            symbols=_split(args.symbols),
            sectors=_split(args.sectors),
        )
        print(counts)
    finally:
        await close_browser()
        await close_client()
        await close_pool()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
