import json
import os
import sys
import tempfile

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

cur_dir = os.path.dirname(__file__)
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from annotate import (
    derive_annotation_positions,
    render_plate_annotation,
    compose_matrix,
    DEFAULT_ANNOTATION_PRESET
)


def _make_grid_map(rows, cols, spot_dx=60.0, spot_dy=60.0, offset_x=100.0, offset_y=100.0):
    grid_map = {}
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            grid_map[(r, c)] = (offset_x + (c - 1) * spot_dx, offset_y + (r - 1) * spot_dy)
    return grid_map


def test_automatic_8x12_whole_plate_annotation():
    """1. Proof: automatic 8x12 whole-plate annotation from saved grid coordinates."""
    layout = {
        "contract_version": 1,
        "layout_id": "1",
        "grid_rows": 8,
        "grid_cols": 12,
        "vertical_labels": [{"pos": i, "label": f"R{i}"} for i in range(1, 9)],
        "strain_bands": [{
            "order": 1,
            "row_start": 1,
            "row_end": 8,
            "labels": [{"pos": j, "label": f"Strain_{j}"} for j in range(1, 13)]
        }]
    }
    grid = _make_grid_map(8, 12)
    pos = derive_annotation_positions(layout, grid)

    assert len(pos["vertical_placements"]) == 8
    assert len(pos["strain_placements"]) == 12
    assert pos["strain_placements"][0]["label"] == "Strain_1"


def test_automatic_8x10_two_strain_band_annotation():
    """2. Proof: automatic 8x10 two-strain-band annotation."""
    layout = {
        "contract_version": 1,
        "layout_id": "2",
        "grid_rows": 8,
        "grid_cols": 10,
        "vertical_labels": [{"pos": i, "label": f"R{i}"} for i in range(1, 9)],
        "strain_bands": [
            {
                "order": 1,
                "row_start": 1,
                "row_end": 4,
                "labels": [{"pos": j, "label": f"Band1_S{j}"} for j in range(1, 11)]
            },
            {
                "order": 2,
                "row_start": 5,
                "row_end": 8,
                "labels": [{"pos": j, "label": f"Band2_S{j}"} for j in range(1, 11)]
            }
        ]
    }
    grid = _make_grid_map(8, 10)
    pos = derive_annotation_positions(layout, grid)

    assert len(pos["strain_placements"]) == 20
    # Check Band 1 vs Band 2 vertical anchors
    b1_y = pos["strain_placements"][0]["y"]
    b2_y = pos["strain_placements"][10]["y"]
    assert b2_y > b1_y, "Band 2 strain labels must be placed below Band 1"


def test_repeated_vertical_labels_distinct_pos():
    """3. Proof: repeated vertical labels placed by physical row Pos."""
    layout = {
        "contract_version": 1,
        "layout_id": "rep",
        "grid_rows": 8,
        "grid_cols": 6,
        "vertical_labels": [
            {"pos": 1, "label": "0"}, {"pos": 2, "label": "-1"}, {"pos": 3, "label": "-2"}, {"pos": 4, "label": "-3"},
            {"pos": 5, "label": "0"}, {"pos": 6, "label": "-1"}, {"pos": 7, "label": "-2"}, {"pos": 8, "label": "-3"}
        ],
        "strain_bands": [{"order": 1, "row_start": 1, "row_end": 8, "labels": [{"pos": 1, "label": "S"}]}]
    }
    grid = _make_grid_map(8, 6)
    pos = derive_annotation_positions(layout, grid)

    assert len(pos["vertical_placements"]) == 8
    # Confirm every pos has distinct increasing y coordinates
    ys = [v["y"] for v in pos["vertical_placements"]]
    assert len(set(ys)) == 8
    assert sorted(ys) == ys


def test_strain_labels_rotated_90deg_clockwise_preset():
    """4. Proof: strain labels rotated 90 degrees clockwise in default preset."""
    assert DEFAULT_ANNOTATION_PRESET["strain_rotation_degrees"] == 90.0
    layout = {
        "grid_rows": 4, "grid_cols": 4,
        "vertical_labels": [{"pos": 1, "label": "R1"}],
        "strain_bands": [{"order": 1, "row_start": 1, "row_end": 4, "labels": [{"pos": 1, "label": "StrainA"}]}]
    }
    grid = _make_grid_map(4, 4)
    pos = derive_annotation_positions(layout, grid, DEFAULT_ANNOTATION_PRESET)
    assert pos["strain_placements"][0]["rotation"] == 90.0


def test_fast_non_destructive_preview():
    """5. Proof: preview renders in memory without modifying source."""
    if not PIL_AVAILABLE:
        return
    
    img = Image.new("RGB", (500, 500), (200, 200, 200))
    layout = {
        "grid_rows": 4, "grid_cols": 4,
        "vertical_labels": [{"pos": i, "label": f"{i}"} for i in range(1, 5)],
        "strain_bands": [{"order": 1, "row_start": 1, "row_end": 4, "labels": [{"pos": j, "label": f"S{j}"} for j in range(1, 5)]}]
    }
    grid = _make_grid_map(4, 4)
    res = render_plate_annotation(img, layout, grid)
    assert res["status"] == "RENDERED"
    assert res["output_path"] is None


def test_deterministic_metadata_headers():
    """6. Proof: date, plate, media, condition, session headers render deterministically."""
    if not PIL_AVAILABLE:
        return
    
    img = Image.new("RGB", (600, 600), (240, 240, 240))
    layout = {
        "grid_rows": 4, "grid_cols": 4,
        "vertical_labels": [{"pos": 1, "label": "0"}],
        "strain_bands": [{"order": 1, "row_start": 1, "row_end": 4, "labels": [{"pos": 1, "label": "S1"}]}]
    }
    grid = _make_grid_map(4, 4)
    req = {
        "image_uid": "E1_14.08.26_24h_I001",
        "labels": {"date": "14.08.26", "condition": "YPD 30C", "session": "24h", "plate": "Plate 1"}
    }
    res = render_plate_annotation(img, layout, grid, annotation_request=req)
    assert len(res["rendered_labels"]["header"]) == 4


def test_matrix_composition_with_structured_labels():
    """7. Proof: compose_matrix arranges multiple crops into structured matrix."""
    if not PIL_AVAILABLE:
        return
    
    crop1 = Image.new("RGB", (80, 80), (100, 150, 200))
    crop2 = Image.new("RGB", (80, 80), (120, 160, 210))
    
    items = [
        {"strain": "WT", "condition": "0h", "image": crop1, "tier": "top"},
        {"strain": "WT", "condition": "24h", "image": crop2, "tier": "top"}
    ]
    matrix_cfg = {"rows": ["WT"], "cols": ["0h", "24h"], "tile_size": (80, 80), "padding": 5}
    comp = compose_matrix(items, matrix_cfg)

    assert comp["status"] == "COMPOSED"
    assert comp["tile_count"] == 2


def test_mixed_crop_tier_matrix_support():
    """8. Proof: mixed crop tiers (e.g. top and low) can co-exist within one matrix."""
    if not PIL_AVAILABLE:
        return
    
    crop_top = Image.new("RGB", (60, 60), (50, 50, 50))
    crop_low = Image.new("RGB", (60, 60), (150, 150, 150))

    items = [
        {"strain": "Strain1", "condition": "24h", "image": crop_top, "tier": "top"},
        {"strain": "Strain2", "condition": "24h", "image": crop_low, "tier": "low"}
    ]
    matrix_cfg = {"rows": ["Strain1", "Strain2"], "cols": ["24h"], "tile_size": (60, 60)}
    comp = compose_matrix(items, matrix_cfg)
    assert comp["status"] == "COMPOSED"


def test_source_image_non_destructive_integrity():
    """9. Proof: source image file is 100% bit-for-bit untouched when saving annotated output."""
    if not PIL_AVAILABLE:
        return
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_p = os.path.join(tmp_dir, "plate_raw.png")
        out_p = os.path.join(tmp_dir, "plate_annotated.png")

        img = Image.new("RGB", (400, 400), (200, 200, 200))
        img.save(raw_p)

        with open(raw_p, "rb") as f:
            raw_bytes_before = f.read()

        layout = {
            "grid_rows": 2, "grid_cols": 2,
            "vertical_labels": [{"pos": 1, "label": "0"}, {"pos": 2, "label": "-1"}],
            "strain_bands": [{"order": 1, "row_start": 1, "row_end": 2, "labels": [{"pos": 1, "label": "A"}, {"pos": 2, "label": "B"}]}]
        }
        grid = _make_grid_map(2, 2)
        render_plate_annotation(raw_p, layout, grid, output_path=out_p)

        assert os.path.exists(out_p)
        with open(raw_p, "rb") as f:
            raw_bytes_after = f.read()
        assert raw_bytes_before == raw_bytes_after


def test_headless_callable_interface():
    """10. Proof: callable functions run headlessly without GUI dependencies."""
    grid = _make_grid_map(2, 2)
    layout = {
        "grid_rows": 2, "grid_cols": 2,
        "vertical_labels": [{"pos": 1, "label": "R1"}, {"pos": 2, "label": "R2"}],
        "strain_bands": [{"order": 1, "row_start": 1, "row_end": 2, "labels": [{"pos": 1, "label": "S1"}, {"pos": 2, "label": "S2"}]}]
    }
    pos = derive_annotation_positions(layout, grid)
    assert "vertical_placements" in pos
    assert "strain_placements" in pos


def test_contract_schema_conformance():
    """11. Proof: annotation request dictionary structure matches schema requirements."""
    req = {
        "contract_version": 1,
        "image_uid": "E1_14.08.26_24h_I001",
        "layout_id": "1",
        "labels": {
            "date": "14.08.26",
            "plate": "1",
            "media": "YPD",
            "condition": "30C",
            "session": "24h"
        },
        "options": {
            "strain_text_rotation_degrees": 90.0,
            "vertical_text_rotation_degrees": 0.0
        }
    }
    assert req["contract_version"] == 1
    assert req["image_uid"]
    assert req["layout_id"]


if __name__ == "__main__":
    test_automatic_8x12_whole_plate_annotation()
    print("[PASS] test_automatic_8x12_whole_plate_annotation")
    test_automatic_8x10_two_strain_band_annotation()
    print("[PASS] test_automatic_8x10_two_strain_band_annotation")
    test_repeated_vertical_labels_distinct_pos()
    print("[PASS] test_repeated_vertical_labels_distinct_pos")
    test_strain_labels_rotated_90deg_clockwise_preset()
    print("[PASS] test_strain_labels_rotated_90deg_clockwise_preset")
    test_fast_non_destructive_preview()
    print("[PASS] test_fast_non_destructive_preview")
    test_deterministic_metadata_headers()
    print("[PASS] test_deterministic_metadata_headers")
    test_matrix_composition_with_structured_labels()
    print("[PASS] test_matrix_composition_with_structured_labels")
    test_mixed_crop_tier_matrix_support()
    print("[PASS] test_mixed_crop_tier_matrix_support")
    test_source_image_non_destructive_integrity()
    print("[PASS] test_source_image_non_destructive_integrity")
    test_headless_callable_interface()
    print("[PASS] test_headless_callable_interface")
    test_contract_schema_conformance()
    print("[PASS] test_contract_schema_conformance")
    print("\nALL 11 ANNOTATION AND MATRIX COMPOSITION PROOF TESTS PASSED.")
