import json
import os
import sys
from typing import Any, Dict

# Ensure local and v10 modules are importable
cur_dir = os.path.dirname(__file__)
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)
v10_dir = os.path.abspath(os.path.join(cur_dir, "..", "v10"))
if v10_dir not in sys.path:
    sys.path.insert(0, v10_dir)

from derive_layout import derive_plate_layout, derive_plate_layout_from_spec, validate_plate_layout
from adapter import load_v10

SAMPLE_PATH = r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx"


def test_single_profile_8x12():
    """1. Proof: 8x12 single-band derivation (14.08.26 / 15.08.26 style)."""
    layout = derive_plate_layout(SAMPLE_PATH, layout_id="1")
    assert layout["contract_version"] == 1
    assert layout["grid_rows"] == 8
    assert layout["grid_cols"] == 12
    assert len(layout["vertical_labels"]) == 8
    assert len(layout["strain_bands"]) == 1
    
    band1 = layout["strain_bands"][0]
    assert band1["order"] == 1
    assert band1["row_start"] == 1
    assert band1["row_end"] == 8
    assert len(band1["labels"]) == 12
    assert [lbl["pos"] for lbl in band1["labels"]] == list(range(1, 13))


def test_two_profile_8x10_even_split():
    """2. Proof: 8x10 two-band derivation with Order and default even row distribution (16.08.26 style)."""
    layout = derive_plate_layout(SAMPLE_PATH, layout_id="2")
    assert layout["grid_rows"] == 8
    assert layout["grid_cols"] == 10
    assert len(layout["strain_bands"]) == 2

    band1, band2 = layout["strain_bands"]
    assert band1["order"] == 1
    assert band1["row_start"] == 1
    assert band1["row_end"] == 4
    assert len(band1["labels"]) == 10

    assert band2["order"] == 2
    assert band2["row_start"] == 5
    assert band2["row_end"] == 8
    assert len(band2["labels"]) == 10


def test_manual_row_band_override():
    """3. Proof: explicit/manual row-band override works deterministically."""
    # Custom spec with 8 rows and 2 bands, but split 2 rows for Band 1, 6 rows for Band 2
    v_labels = [{"pos": i, "label": f"R{i}"} for i in range(1, 9)]
    s_specs = [
        {"order": 1, "profile": "P1", "labels": [{"pos": j, "label": f"S1_{j}"} for j in range(1, 11)]},
        {"order": 2, "profile": "P2", "labels": [{"pos": j, "label": f"S2_{j}"} for j in range(1, 11)]}
    ]
    custom_layout = derive_plate_layout_from_spec(
        layout_id="custom_override",
        vertical_labels=v_labels,
        strain_bands_spec=s_specs,
        row_band_overrides=[(1, 2), (3, 8)]
    )
    assert custom_layout["grid_rows"] == 8
    assert custom_layout["grid_cols"] == 10
    assert custom_layout["strain_bands"][0]["row_start"] == 1
    assert custom_layout["strain_bands"][0]["row_end"] == 2
    assert custom_layout["strain_bands"][1]["row_start"] == 3
    assert custom_layout["strain_bands"][1]["row_end"] == 8


def test_widest_band_wins_overall_cols():
    """4. Proof: widest-band-wins determines overall grid_cols."""
    v_labels = [{"pos": i, "label": f"R{i}"} for i in range(1, 9)]
    s_specs = [
        {"order": 1, "profile": "WideBand", "labels": [{"pos": j, "label": f"W{j}"} for j in range(1, 11)]},
        {"order": 2, "profile": "NarrowBand", "labels": [{"pos": j, "label": f"N{j}"} for j in range(1, 5)]}
    ]
    layout = derive_plate_layout_from_spec(
        layout_id="unequal_widths",
        vertical_labels=v_labels,
        strain_bands_spec=s_specs
    )
    assert layout["grid_cols"] == 10  # 10 vs 4 -> 10 wins
    assert layout["grid_rows"] == 8


def test_unequal_band_widths_local_vs_global():
    """5. Proof: unequal-width bands preserve local column lengths independently of global grid_cols."""
    v_labels = [{"pos": i, "label": f"R{i}"} for i in range(1, 9)]
    s_specs = [
        {"order": 1, "profile": "Band10", "labels": [{"pos": j, "label": f"W{j}"} for j in range(1, 11)]},
        {"order": 2, "profile": "Band4", "labels": [{"pos": j, "label": f"N{j}"} for j in range(1, 5)]}
    ]
    layout = derive_plate_layout_from_spec(
        layout_id="unequal_widths_local",
        vertical_labels=v_labels,
        strain_bands_spec=s_specs
    )
    band1 = layout["strain_bands"][0]
    band2 = layout["strain_bands"][1]
    
    assert len(band1["labels"]) == 10
    assert [l["pos"] for l in band1["labels"]] == list(range(1, 11))

    assert len(band2["labels"]) == 4
    assert [l["pos"] for l in band2["labels"]] == list(range(1, 5))


def test_repeated_vertical_labels_distinct_pos():
    """6. Proof: repeated vertical label text still yields separate rows via Pos."""
    # Pattern of 8 rows with repeated labels '0', '-1', '-2', '-3', '0', '-1', '-2', '-3'
    v_labels = [
        {"pos": 1, "label": "0"},
        {"pos": 2, "label": "-1"},
        {"pos": 3, "label": "-2"},
        {"pos": 4, "label": "-3"},
        {"pos": 5, "label": "0"},
        {"pos": 6, "label": "-1"},
        {"pos": 7, "label": "-2"},
        {"pos": 8, "label": "-3"}
    ]
    s_specs = [
        {"order": 1, "profile": "P1", "labels": [{"pos": 1, "label": "StrainA"}, {"pos": 2, "label": "StrainB"}]}
    ]
    layout = derive_plate_layout_from_spec(
        layout_id="repeated_vert",
        vertical_labels=v_labels,
        strain_bands_spec=s_specs
    )
    assert layout["grid_rows"] == 8
    assert len(layout["vertical_labels"]) == 8
    assert [v["pos"] for v in layout["vertical_labels"]] == list(range(1, 9))
    assert [v["label"] for v in layout["vertical_labels"]] == ["0", "-1", "-2", "-3", "0", "-1", "-2", "-3"]


def test_ambiguous_and_invalid_inputs_fail_clearly():
    """7. Proof: ambiguous and invalid inputs fail clearly with ValueError."""
    v_labels_8 = [{"pos": i, "label": f"R{i}"} for i in range(1, 9)]
    v_labels_7 = [{"pos": i, "label": f"R{i}"} for i in range(1, 8)]
    s_specs_2 = [
        {"order": 1, "profile": "P1", "labels": [{"pos": 1, "label": "A"}]},
        {"order": 2, "profile": "P2", "labels": [{"pos": 1, "label": "B"}]}
    ]

    # Non-divisible rows (7 rows / 2 bands) without overrides
    try:
        derive_plate_layout_from_spec("invalid_split", v_labels_7, s_specs_2)
        assert False, "Should have raised ValueError for non-divisible row count"
    except ValueError as e:
        assert "Cannot evenly divide" in str(e)

    # Duplicate Pos in strain band
    s_specs_dup = [
        {"order": 1, "profile": "P1", "labels": [{"pos": 1, "label": "A"}, {"pos": 1, "label": "B"}]}
    ]
    try:
        derive_plate_layout_from_spec("dup_pos", v_labels_8, s_specs_dup)
        assert False, "Should have raised ValueError for duplicate Pos"
    except ValueError as e:
        assert "Duplicate positions" in str(e)


def test_contract_schema_conformance():
    """8. Proof: output validates strictly against PlateLayout v1 contract."""
    pm = load_v10(SAMPLE_PATH)
    img1 = pm["images"][0]["image_uid"]
    layout1 = derive_plate_layout(SAMPLE_PATH, image_uid=img1)
    
    # Check all schema required fields
    assert layout1["contract_version"] == 1
    assert "layout_id" in layout1
    assert "grid_rows" in layout1
    assert "grid_cols" in layout1
    assert "vertical_labels" in layout1
    assert "strain_bands" in layout1
    validate_plate_layout(layout1)

    # Also test image with layout 2 (multi-band)
    img_set2 = next(img["image_uid"] for img in pm["images"] if img["session_uid"] == "E2_16.08.26_24h")
    layout2 = derive_plate_layout(SAMPLE_PATH, image_uid=img_set2)
    validate_plate_layout(layout2)


if __name__ == "__main__":
    test_single_profile_8x12()
    print("[PASS] test_single_profile_8x12")
    test_two_profile_8x10_even_split()
    print("[PASS] test_two_profile_8x10_even_split")
    test_manual_row_band_override()
    print("[PASS] test_manual_row_band_override")
    test_widest_band_wins_overall_cols()
    print("[PASS] test_widest_band_wins_overall_cols")
    test_unequal_band_widths_local_vs_global()
    print("[PASS] test_unequal_band_widths_local_vs_global")
    test_repeated_vertical_labels_distinct_pos()
    print("[PASS] test_repeated_vertical_labels_distinct_pos")
    test_ambiguous_and_invalid_inputs_fail_clearly()
    print("[PASS] test_ambiguous_and_invalid_inputs_fail_clearly")
    test_contract_schema_conformance()
    print("[PASS] test_contract_schema_conformance")
    print("\nALL 8 PLATE LAYOUT DERIVATION PROOF TESTS PASSED.")
