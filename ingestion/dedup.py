"""Dedup theo content_hash = sha256(text_norm)."""

import hashlib


def content_hash(text_norm: str) -> str:
    return hashlib.sha256(text_norm.encode("utf-8")).hexdigest()
