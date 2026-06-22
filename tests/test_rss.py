from ingestion.rss import parse_feed

_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Chứng khoán - Google Tin tức</title>
    <item>
      <title>VCB tăng trần phiên cuối tuần</title>
      <link>https://example.com/vcb-tang-tran</link>
      <pubDate>Mon, 26 Jan 2026 03:06:18 GMT</pubDate>
      <source url="https://cafef.vn">CafeF</source>
    </item>
    <item>
      <title>Giá dầu Brent giảm mạnh</title>
      <link>https://example.com/gia-dau-brent</link>
      <pubDate>Sun, 25 Jan 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Tin thiếu link</title>
    </item>
  </channel>
</rss>
"""


def test_parse_feed_extracts_items():
    items = parse_feed(_SAMPLE, source_name="GoogleNews:test")

    # Bỏ item thiếu link -> còn 2
    assert len(items) == 2

    first = items[0]
    assert first.url == "https://example.com/vcb-tang-tran"
    assert first.title == "VCB tăng trần phiên cuối tuần"
    assert first.published_at is not None
    assert first.published_at.year == 2026
    # entry.source.title được ưu tiên làm source
    assert first.source == "CafeF"


def test_parse_feed_falls_back_to_source_name():
    items = parse_feed(_SAMPLE, source_name="GoogleNews:test")
    # item thứ 2 không có <source> -> dùng source_name
    assert items[1].source == "GoogleNews:test"
