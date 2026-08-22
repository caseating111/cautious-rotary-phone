
from adapter import load_v10, extract_layouts


def test_load_v10():
    pm = load_v10(r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx")
    assert pm["contract_version"] == 1
    assert len(pm["images"]) == 98
    assert len(pm["sessions"]) == 4

def test_extract_layouts():
    layouts = extract_layouts(r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx")
    assert len(layouts) == 2
    l1 = layouts["annotationSet 1"]
    assert l1["grid_rows"] == 8
    assert l1["grid_cols"] == 12
    l2 = layouts["annotationSet 2"]
    assert l2["grid_rows"] == 8
    assert l2["grid_cols"] == 20
