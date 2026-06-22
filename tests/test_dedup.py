from ingestion import dedup
from ingestion.normalize import normalize


def test_content_hash_stable_and_distinct():
    h1 = dedup.content_hash("vcb tăng trần")
    h2 = dedup.content_hash("vcb tăng trần")
    h3 = dedup.content_hash("hpg giảm sàn")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex


def test_normalize_collapses_whitespace_and_lowercases():
    title_norm, text_norm = normalize("  VCB   Tăng\nTrần ", "Nội   dung\t Bài")
    assert title_norm == "vcb tăng trần"
    assert text_norm == "nội dung bài"
