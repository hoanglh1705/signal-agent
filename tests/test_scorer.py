from ingestion import scorer


def test_parse_handles_code_fence():
    raw = '```json\n{"impact": 0.5, "summary": "x"}\n```'
    data = scorer._parse(raw)
    assert data["impact"] == 0.5
    assert data["summary"] == "x"


def test_clamp_bounds_and_default():
    assert scorer._clamp(2.0, 0.0, 1.0) == 1.0
    assert scorer._clamp(-5, -1.0, 1.0) == -1.0
    assert scorer._clamp("bad", 0.0, 1.0, default=0.0) == 0.0


def test_norm_symbols_objects_and_strings():
    out = scorer._norm_symbols(
        [
            {"symbol": "vcb", "impact": 1.5, "stance": -2.0},
            "ctg",
            {"symbol": ""},  # bỏ
        ]
    )
    assert out[0] == {"symbol": "VCB", "impact": 1.0, "stance": -1.0}
    assert out[1] == {"symbol": "CTG", "impact": 0.0, "stance": 0.0}
    assert len(out) == 2
