from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from clients.http import close_client
from db.pool import close_pool
from graph import run_signal_graph
from ingestion import pipeline
from ingestion.gnews_resolver import close_browser
from schemas import SignalRequest, SignalResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown: đóng browser + http client + db pool
    await close_browser()
    await close_client()
    await close_pool()


app = FastAPI(title="signal-agent", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/signals/generate", response_model=SignalResponse)
async def generate_signal(req: SignalRequest):
    result = await run_signal_graph(req)
    return SignalResponse(**result)


class IngestRequest(BaseModel):
    symbols: list[str] = []
    sectors: list[str] = []


@app.post("/v1/ingest")
async def ingest(req: IngestRequest):
    """Chạy ingestion đồng bộ và trả về counts theo status."""
    counts = await pipeline.run_once(symbols=req.symbols, sectors=req.sectors)
    return counts
