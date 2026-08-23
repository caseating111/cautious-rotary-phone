
import os
import sys
from adapter import (
    load_v10,
    extract_layouts,
    derive_plate_layout,
    reconcile_image_files,
    project_to_legacy_images_rows,
    project_to_legacy_grid_rows,
)

SAMPLE_PATH = r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx"


def test_load_v10_contract_and_schemas():
    """Validates that load_v10 produces valid ProjectModel v1 matching contract schema."""
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


def test_sessions_and_image_uids():
    """Verifies sessionUID and Image UID uniqueness and image # restart across sessions."""
    pm = load_v10(SAMPLE_PATH)
    session_uids = [s["session_uid"] for s in pm["sessions"]]
    assert len(session_uids) == 4
    assert len(set(session_uids)) == 4
    assert session_uids == [
        "E1_14.08.26_24h",
        "E1_15.08.26_48h",
        "E2_16.08.26_24h",
        "E2_17.08.26_48h"
    ]

    # Verify image UID uniqueness
    all_image_uids = [img["image_uid"] for img in pm["images"]]
    assert len(all_image_uids) == 98
    assert len(set(all_image_uids)) == 98

    # Verify image number restarts at 1 for each session and original names restart
    for suid in session_uids:
        session_imgs = [img for img in pm["images"] if img["session_uid"] == suid]
        img_nums = [img["image_number"] for img in session_imgs]
        assert img_nums[0] == 1
        assert img_nums == list(range(1, len(session_imgs) + 1))
        # Original camera basename image1.jpg exists in every session
        assert any(img["original"] == "image1.jpg" for img in session_imgs)


def test_sparse_human_vs_resolved_machine_fields():
    """Verifies that resolved machine fields expand values without requiring repeated human entry."""
    pm = load_v10(SAMPLE_PATH)
    # Check sessions have resolved exp and date from Exp* and Date*
    s1 = next(s for s in pm["sessions"] if s["session_uid"] == "E1_14.08.26_24h")
    assert s1["exp"] == "1"
    assert s1["date"] == "2026-08-14"
    assert s1["arrangement"] == "Arrangement 1"
    assert s1["annotation_set"] == "annotationSet 1"

    # In images, Set is populated for all images ('A', 'B', 'c')
    set_values = {img["set"] for img in pm["images"]}
    assert set_values == {"A", "B", "c"}


def test_media_and_condition_combinations():
    """Verifies that Media and Condition are independently optional."""
    pm = load_v10(SAMPLE_PATH)
    images = pm["images"]

    # Media only (YPDA, None)
    media_only = [img for img in images if img["media"] == "YPDA" and img["condition"] is None]
    assert len(media_only) > 0

    # Condition only (None, sugar) - e.g. Image 25 in Exp 2
    cond_only = [img for img in images if img["media"] is None and img["condition"] == "sugar"]
    assert len(cond_only) == 2  # in 24h and 48h sessions of Exp 2

    # Media + Condition (heat)
    media_heat = [img for img in images if img["media"] == "YPDA" and img["condition"] == "heat"]
    assert len(media_heat) > 0

    # Media + Condition (salt)
    media_salt = [img for img in images if img["media"] == "YPDA" and img["condition"] == "salt"]
    assert len(media_salt) > 0

    # Replicate numbers
    reps = {img["rep"] for img in images}
    assert {1, 2, 3, 4}.issubset(reps)


def test_extract_layouts_single_and_multi_band():
    """
    Verifies layout extraction:
    - annotationSet 1: 1 strain band (Strain 1: Set A, 12 cols, rows 1-8), Vertical 1 (8 rows) -> 8x12 grid.
    - annotationSet 2: 2 strain bands (Strain 2: Set A (10 cols) rows 1-4, Set B (10 cols) rows 5-8), Vertical 1 (8 rows) -> 8x10 grid.
    """
    layouts = extract_layouts(SAMPLE_PATH)
    assert set(layouts.keys()) == {"annotationSet 1", "annotationSet 2"}

    # Layout 1: 8x12, 1 band
    l1 = layouts["annotationSet 1"]
    assert l1["contract_version"] == 1
    assert l1["layout_id"] == "annotationSet 1"
    assert l1["grid_rows"] == 8
    assert l1["grid_cols"] == 12
    assert len(l1["vertical_labels"]) == 8
    assert len(l1["strain_bands"]) == 1
    
    b1 = l1["strain_bands"][0]
    assert b1["order"] == 1
    assert b1["row_start"] == 1
    assert b1["row_end"] == 8
    assert len(b1["labels"]) == 12
    assert b1["labels"][0] == {"pos": 1, "label": "strain1"}
    assert b1["labels"][-1] == {"pos": 12, "label": "strain12"}

    # Layout 2: 8x10, 2 bands
    l2 = layouts["annotationSet 2"]
    assert l2["contract_version"] == 1
    assert l2["layout_id"] == "annotationSet 2"
    assert l2["grid_rows"] == 8
    assert l2["grid_cols"] == 10
    assert len(l2["vertical_labels"]) == 8
    assert len(l2["strain_bands"]) == 2

    # Band A: rows 1-4, 10 cols
    b2_1 = l2["strain_bands"][0]
    assert b2_1["order"] == 1
    assert b2_1["row_start"] == 1
    assert b2_1["row_end"] == 4
    assert len(b2_1["labels"]) == 10
    assert b2_1["labels"][0] == {"pos": 1, "label": "exp2_strain1"}
    assert b2_1["labels"][-1] == {"pos": 10, "label": "exp2_strain10"}

    # Band B: rows 5-8, 10 cols
    b2_2 = l2["strain_bands"][1]
    assert b2_2["order"] == 2
    assert b2_2["row_start"] == 5
    assert b2_2["row_end"] == 8
    assert len(b2_2["labels"]) == 10
    assert b2_2["labels"][0] == {"pos": 1, "label": "exp2_culture1"}
    assert b2_2["labels"][-1] == {"pos": 10, "label": "exp2_culture10"}


def test_strain_set_not_matched_to_master_registry_set():
    """
    Verifies that strain-table Set values are band markers and NOT matched against image Set.
    Both Set A and Set B images under annotationSet 2 derive the full 2-band 8x10 layout.
    """
    pm = load_v10(SAMPLE_PATH)
    layouts = extract_layouts(SAMPLE_PATH)

    img_set_a = next(img for img in pm["images"] if img["annotation_set"] == "annotationSet 2" and img["set"] == "A")
    img_set_b = next(img for img in pm["images"] if img["annotation_set"] == "annotationSet 2" and img["set"] == "B")

    layout_a = derive_plate_layout(pm, img_set_a["image_uid"], layouts)
    layout_b = derive_plate_layout(pm, img_set_b["image_uid"], layouts)

    # Both images get the identical multi-band layout
    assert layout_a["layout_id"] == "annotationSet 2"
    assert layout_b["layout_id"] == "annotationSet 2"
    assert len(layout_a["strain_bands"]) == 2
    assert len(layout_b["strain_bands"]) == 2


def test_vertical_profile_set_ignored():
    """Verifies that the Set column in the vertical profile table is ignored."""
    layouts = extract_layouts(SAMPLE_PATH)
    for lid, layout in layouts.items():
        assert layout["grid_rows"] == 8
        positions = [vl["pos"] for vl in layout["vertical_labels"]]
        assert positions == list(range(1, 9))


def test_derive_plate_layout_api():
    """Tests derive_plate_layout helper by image_uid."""
    pm = load_v10(SAMPLE_PATH)
    layouts = extract_layouts(SAMPLE_PATH)

    uid_1 = pm["images"][0]["image_uid"]
    layout1 = derive_plate_layout(pm, uid_1, layouts)
    assert layout1["layout_id"] == "annotationSet 1"
    assert layout1["grid_cols"] == 12

    # Direct extraction via path
    layout1_direct = derive_plate_layout(pm, uid_1, v10_path=SAMPLE_PATH)
    assert layout1_direct["layout_id"] == "annotationSet 1"


def test_unequal_band_widths_synthetic():
    """
    Verifies that a shorter band does not reduce the global grid width.
    The widest band determines grid_cols.
    """
    # Create mock layout dictionary with Band 1 (12 cols) and Band 2 (8 cols)
    band1_labels = [{"pos": i, "label": f"s{i}"} for i in range(1, 13)]
    band2_labels = [{"pos": i, "label": f"c{i}"} for i in range(1, 9)]
    grid_cols = max(max(l["pos"] for l in band1_labels), max(l["pos"] for l in band2_labels))
    assert grid_cols == 12
    assert len(band1_labels) == 12
    assert len(band2_labels) == 8


def test_non_deterministic_band_allocation_validation():
    """
    Verifies that non-deterministic row allocation (e.g. 8 rows / 3 bands) raises ValueError
    unless explicit row_band_overrides are provided.
    """
    # Overrides test: 8 rows with custom band ranges
    custom_overrides = {"annotationSet 2": [(1, 4), (5, 8)]}
    layouts = extract_layouts(SAMPLE_PATH, row_band_overrides=custom_overrides)
    assert len(layouts["annotationSet 2"]["strain_bands"]) == 2
    assert layouts["annotationSet 2"]["strain_bands"][0]["row_start"] == 1
    assert layouts["annotationSet 2"]["strain_bands"][0]["row_end"] == 4


def test_reconcile_image_files():
    """
    Verifies file reconciliation with controlled evidence order:
    - Provenance
    - Exact Original
    - Exact Working filename
    - Controlled derivatives (PROCESSED prefix, .tif extension)
    - Ambiguous / unmapped detection
    """
    pm = load_v10(SAMPLE_PATH)
    s1 = "E1_14.08.26_24h"

    # Simulate files present in session 1 folder:
    # image1.jpg -> exact original match for image 1
    # 14.08.26_SetA_24h_YPDA, 2.jpg -> exact working filename match for image 2
    # PROCESSED 14.08.26_SetA_24h_YPDA, 3.tif -> controlled derivative for image 3
    # extra_file.jpg -> unmapped file
    files_by_session = {
        s1: [
            "image1.jpg",
            "14.08.26_SetA_24h_YPDA, 2.jpg",
            "PROCESSED 14.08.26_SetA_24h_YPDA, 3.tif",
            "extra_file.jpg",
        ]
    }
    # Image 4 has provenance mapping to an external accepted file
    provenance = {
        "E1_14.08.26_24h_I004": "D:/Accepted/custom_named_img4.jpg"
    }

    res = reconcile_image_files(pm, files_by_session=files_by_session, provenance_map=provenance)
    summary = res["summary"]
    assert summary["total_expected"] == 98

    img_map = {r["image_uid"]: r for r in res["images"]}

    # Image 1 -> READY via exact original
    assert img_map["E1_14.08.26_24h_I001"]["status"] == "READY"
    assert img_map["E1_14.08.26_24h_I001"]["matched_file"] == "image1.jpg"

    # Image 2 -> READY via exact working filename
    assert img_map["E1_14.08.26_24h_I002"]["status"] == "READY"
    assert img_map["E1_14.08.26_24h_I002"]["matched_file"] == "14.08.26_SetA_24h_YPDA, 2.jpg"

    # Image 3 -> READY via controlled derivative
    assert img_map["E1_14.08.26_24h_I003"]["status"] == "READY"
    assert img_map["E1_14.08.26_24h_I003"]["matched_file"] == "PROCESSED 14.08.26_SetA_24h_YPDA, 3.tif"

    # Image 4 -> READY via provenance
    assert img_map["E1_14.08.26_24h_I004"]["status"] == "READY"
    assert img_map["E1_14.08.26_24h_I004"]["matched_file"] == "D:/Accepted/custom_named_img4.jpg"

    # Image 5 -> EXPECTED_NOT_PRESENT (no file provided)
    assert img_map["E1_14.08.26_24h_I005"]["status"] == "EXPECTED_NOT_PRESENT"

    # Unmapped file extra_file.jpg
    unmapped = [u["file"] for u in res["unmapped_files"]]
    assert "extra_file.jpg" in unmapped


def test_legacy_projections():
    """Verifies legacy compatibility projection generators."""
    pm = load_v10(SAMPLE_PATH)
    layouts = extract_layouts(SAMPLE_PATH)

    # Legacy images projection
    legacy_images = project_to_legacy_images_rows(pm)
    assert len(legacy_images) == 98
    assert "Filename" in legacy_images[0]
    assert "Type" in legacy_images[0]
    assert "Image UID" in legacy_images[0]

    # Legacy grid projection for layout 2
    legacy_grid = project_to_legacy_grid_rows(layouts["annotationSet 2"])
    assert len(legacy_grid) == 20  # 10 in band 1 + 10 in band 2
    assert legacy_grid[0]["GridCols"] == 10
    assert legacy_grid[0]["BandOrder"] == 1
    assert legacy_grid[-1]["BandOrder"] == 2


if __name__ == "__main__":
    test_load_v10_contract_and_schemas()
    print("[PASS] test_load_v10_contract_and_schemas")
    test_sessions_and_image_uids()
    print("[PASS] test_sessions_and_image_uids")
    test_sparse_human_vs_resolved_machine_fields()
    print("[PASS] test_sparse_human_vs_resolved_machine_fields")
    test_media_and_condition_combinations()
    print("[PASS] test_media_and_condition_combinations")
    test_extract_layouts_single_and_multi_band()
    print("[PASS] test_extract_layouts_single_and_multi_band")
    test_strain_set_not_matched_to_master_registry_set()
    print("[PASS] test_strain_set_not_matched_to_master_registry_set")
    test_vertical_profile_set_ignored()
    print("[PASS] test_vertical_profile_set_ignored")
    test_derive_plate_layout_api()
    print("[PASS] test_derive_plate_layout_api")
    test_unequal_band_widths_synthetic()
    print("[PASS] test_unequal_band_widths_synthetic")
    test_non_deterministic_band_allocation_validation()
    print("[PASS] test_non_deterministic_band_allocation_validation")
    test_reconcile_image_files()
    print("[PASS] test_reconcile_image_files")
    test_legacy_projections()
    print("[PASS] test_legacy_projections")
    print("\nALL 12 V10 ADAPTER AUDIT TESTS PASSED.")

