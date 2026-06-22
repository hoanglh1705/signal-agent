"""Mirror nhẹ của model articles / article_scores bên Go (signal-engine).

Chỉ dùng cho type-safety nội bộ + hằng số status. Bảng thật do Go định nghĩa.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ArticleStatus:
    NEW = "NEW"
    FETCHED = "FETCHED"
    SCORED = "SCORED"
    DUPLICATE = "DUPLICATE"
    ERROR = "ERROR"


class ArticleRow(BaseModel):
    id: str | None = None
    url: str
    source: str = ""
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    title: str = ""
    text: str = ""
    title_norm: str = ""
    text_norm: str = ""
    content_hash: str = ""
    status: str = ArticleStatus.NEW


class ArticleScoreRow(BaseModel):
    article_id: str
    run_id: str = ""
    impact: float = 0.0
    relevance: float = 0.0
    stance: float = 0.0
    magnitude: float = 0.0
    source_trust: float = 0.0
    novelty: float = 0.0
    time_decay: float = 0.0
    topics: list[Any] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    reasons: dict[str, Any] = Field(default_factory=dict)
