"""Parse RSS feed (Google News + báo VN) bằng feedparser."""

from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


@dataclass
class FeedItem:
    url: str
    title: str
    published_at: datetime | None
    source: str


def _to_datetime(entry) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not parsed:
        return None
    # struct_time (UTC) -> datetime aware
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def parse_feed(content: str | bytes, source_name: str) -> list[FeedItem]:
    """Parse nội dung feed (string/bytes) -> list FeedItem.

    Tách parse khỏi fetch để dễ test bằng fixture.
    """
    parsed = feedparser.parse(content)
    items: list[FeedItem] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", "")
        title = getattr(entry, "title", "")
        if not link or not title:
            continue
        # Google News gắn tên nguồn gốc ở entry.source.title nếu có.
        src = source_name
        entry_source = getattr(entry, "source", None)
        if entry_source is not None:
            src = getattr(entry_source, "title", None) or source_name
        items.append(
            FeedItem(
                url=link,
                title=title,
                published_at=_to_datetime(entry),
                source=src,
            )
        )
    return items
