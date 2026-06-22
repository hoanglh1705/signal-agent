import os

# Settings yêu cầu các biến này lúc import config -> set trước khi test chạy.
os.environ.setdefault("OPENAPI_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
