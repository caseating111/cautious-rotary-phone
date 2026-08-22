
import os
import sys
from adapter import load_v10, extract_layouts

SAMPLE_PATH = r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx"

def test_load_v10_contract():
    pm = load_v10(SAMPLE_PATH)
    assert pm["contract_version"] == 1, "Must have contract_version: 1"
    
    # Validate sessions
    assert isinstance(pm["sessions"], list) and len(pm["sessions"]) == 4
    for s in pm["sessions"]:
        allowed_session_keys = {"session_uid", "exp", "date", "time", "name", "arrangement", "annotation_set"}
        assert set(s.keys()) == allowed_session_keys, f"Session keys mismatch: {set(s.keys())}"
        assert isinstance(s["session_uid"], str) and len(s["session_uid"]) >= 1
        assert isinstance(s["exp"], str) and len(s["exp"]) >= 1
        assert isinstance(s["date"], str) and len(s["date"]) >= 1
        assert s["time"] is None or isinstance(s["time"], str)
        assert s["name"] is None or isinstance(s["name"], str)
        assert s["arrangement"] is None or isinstance(s["arrangement"], str)
        assert s["annotation_set"] is None or isinstance(s["annotation_set"], str)
        
    # Validate images
    assert isinstance(pm["images"], list) and len(pm["images"]) == 98
    for img in pm["images"]:
        allowed_img_keys = {
            "image_uid", "session_uid", "image_number", "original",
            "working_filename", "exp", "set", "media", "condition",
            "rep", "arrangement", "annotation_set"
        }
        assert set(img.keys()) == allowed_img_keys, f"Image keys mismatch: {set(img.keys())}"
        assert isinstance(img["image_uid"], str) and len(img["image_uid"]) >= 1
        assert isinstance(img["session_uid"], str) and len(img["session_uid"]) >= 1
        assert isinstance(img["image_number"], int) and img["image_number"] >= 1
        assert isinstance(img["original"], str) and len(img["original"]) >= 1
        assert img["working_filename"] is None or isinstance(img["working_filename"], str)
        assert isinstance(img["exp"], str) and len(img["exp"]) >= 1
        assert isinstance(img["set"], str) and len(img["set"]) >= 1
        assert img["media"] is None or isinstance(img["media"], str)
        assert img["condition"] is None or isinstance(img["condition"], str)
        assert img["rep"] is None or isinstance(img["rep"], (int, str))
        assert img["arrangement"] is None or isinstance(img["arrangement"], str)
        assert img["annotation_set"] is None or isinstance(img["annotation_set"], str)

def test_extract_layouts_contract():
    layouts = extract_layouts(SAMPLE_PATH)
    assert isinstance(layouts, dict) and len(layouts) == 2
    
    for lid, l in layouts.items():
        allowed_layout_keys = {"contract_version", "layout_id", "grid_rows", "grid_cols", "vertical_labels", "strain_bands"}
        assert set(l.keys()) == allowed_layout_keys, f"Layout keys mismatch: {set(l.keys())}"
        assert l["contract_version"] == 1
        assert isinstance(l["layout_id"], str) and len(l["layout_id"]) >= 1
        assert isinstance(l["grid_rows"], int) and l["grid_rows"] >= 1
        assert isinstance(l["grid_cols"], int) and l["grid_cols"] >= 1
        
        # vertical_labels
        assert isinstance(l["vertical_labels"], list) and len(l["vertical_labels"]) == l["grid_rows"]
        for vl in l["vertical_labels"]:
            assert set(vl.keys()) == {"pos", "label"}
            assert isinstance(vl["pos"], int) and vl["pos"] >= 1
            assert isinstance(vl["label"], str)
            
        # strain_bands
        assert isinstance(l["strain_bands"], list) and len(l["strain_bands"]) >= 1
        for sb in l["strain_bands"]:
            allowed_sb_keys = {"order", "profile", "row_start", "row_end", "labels"}
            assert set(sb.keys()) == allowed_sb_keys
            assert isinstance(sb["order"], int) and sb["order"] >= 1
            assert sb["profile"] is None or isinstance(sb["profile"], str)
            assert isinstance(sb["row_start"], int) and sb["row_start"] >= 1
            assert isinstance(sb["row_end"], int) and sb["row_end"] >= 1
            assert isinstance(sb["labels"], list) and len(sb["labels"]) >= 1
            for lbl in sb["labels"]:
                assert set(lbl.keys()) == {"pos", "label"}
                assert isinstance(lbl["pos"], int) and lbl["pos"] >= 1
                assert isinstance(lbl["label"], str)
                
    # Specific layout properties
    l1 = layouts["annotationSet 1"]
    assert l1["grid_rows"] == 8
    assert l1["grid_cols"] == 12
    assert len(l1["strain_bands"]) == 1
    assert l1["strain_bands"][0]["labels"][0]["label"] == "strain1"
    assert l1["strain_bands"][0]["labels"][-1]["label"] == "strain12"
    
    l2 = layouts["annotationSet 2"]
    assert l2["grid_rows"] == 8
    assert l2["grid_cols"] == 20
    assert len(l2["strain_bands"]) == 1
    assert l2["strain_bands"][0]["labels"][0]["label"] == "exp2_strain1"

if __name__ == "__main__":
    test_load_v10_contract()
    print("[PASS] test_load_v10_contract")
    test_extract_layouts_contract()
    print("[PASS] test_extract_layouts_contract")
    print("ALL V10 ADAPTER VALIDATION TESTS PASSED SUCCESSFULLY.")
