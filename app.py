from fastapi import FastAPI

from graph import run_signal_graph
from schemas import SignalRequest, SignalResponse

app = FastAPI(title="signal-agent")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/signals/generate", response_model=SignalResponse)
async def generate_signal(req: SignalRequest):
    
    result = await run_signal_graph(req)
    print(result)
    
    return SignalResponse(**result)