"""Chuẩn hoá title/text để dedup và lọc (mirror bước Normalize của Go)."""

import re

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip().lower())


def normalize(title: str, text: str) -> tuple[str, str]:
    return _norm(title), _norm(text)
