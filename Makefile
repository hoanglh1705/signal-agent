run-watch:
	uv run uvicorn app:app --reload --port 8010

# Chạy ingestion một lượt. Tuỳ chọn: make ingest SYMBOLS=VCB,FPT SECTORS=banking
ingest:
	uv run python -m ingestion.run --symbols "$(SYMBOLS)" --sectors "$(SECTORS)"

test:
	uv run pytest -q
