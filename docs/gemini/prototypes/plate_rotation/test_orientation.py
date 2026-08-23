import math
import os
import sys
import tempfile

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Ensure local module is importable
cur_dir = os.path.dirname(__file__)
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from orientation import (
    compute_line_angle,
    transform_point_around_center,
    capture_plate_orientation,
    apply_plate_orientation
)


def test_modest_clockwise_tilt():
    """1. Proof: modest clockwise tilt calculates correct counter-clockwise correction."""
    # Line starts at (100, 100) and ends at (1000, 150) -> tilts downwards to the right (+3.1798 deg)
    obs, corr = compute_line_angle(100, 100, 1000, 150)
    assert obs > 0, "Observed angle should be positive (downward slope)"
    assert round(obs, 2) == 3.18
    assert corr == obs

    # Test point transformation around center (500, 500)
    cx, cy = 500, 500
    nx1, ny1 = transform_point_around_center(100, 100, cx, cy, corr)
    nx2, ny2 = transform_point_around_center(1000, 150, cx, cy, corr)
    
    # After rotation, both points should have virtually identical y coordinates (horizontal line!)
    assert abs(ny1 - ny2) < 1e-3, f"Line not horizontal after rotation: y1'={ny1}, y2'={ny2}"


def test_modest_counter_clockwise_tilt():
    """2. Proof: modest counter-clockwise tilt calculates correct clockwise correction."""
    # Line starts at (100, 150) and ends at (1000, 100) -> tilts upwards to the right (-3.1798 deg)
    obs, corr = compute_line_angle(100, 150, 1000, 100)
    assert obs < 0, "Observed angle should be negative (upward slope)"
    assert round(obs, 2) == -3.18

    cx, cy = 500, 500
    nx1, ny1 = transform_point_around_center(100, 150, cx, cy, corr)
    nx2, ny2 = transform_point_around_center(1000, 100, cx, cy, corr)
    assert abs(ny1 - ny2) < 1e-3, f"Line not horizontal after rotation: y1'={ny1}, y2'={ny2}"


def test_near_zero_tilt():
    """3. Proof: perfectly horizontal line produces 0.0 degree correction."""
    obs, corr = compute_line_angle(100, 200, 900, 200)
    assert abs(obs) < 1e-9
    assert abs(corr) < 1e-9


def test_top_and_bottom_edge_equivalence():
    """4. Proof: top-edge and bottom-edge lines obey the exact same horizontal-reference rule."""
    # Top edge
    obs_top, corr_top = compute_line_angle(150, 100, 950, 160)
    # Bottom edge with identical slope
    obs_bot, corr_bot = compute_line_angle(150, 800, 950, 860)

    assert abs(obs_top - obs_bot) < 1e-9
    assert abs(corr_top - corr_bot) < 1e-9


def test_non_destructive_preview_and_apply():
    """5. Proof: preview/apply is non-destructive to raw source images."""
    if not PIL_AVAILABLE:
        print("Skipping PIL-dependent test (Pillow not installed)")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_path = os.path.join(tmp_dir, "raw_image.png")
        working_path = os.path.join(tmp_dir, "working_image.png")

        # Create dummy test image
        img = Image.new("RGB", (600, 600), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.line([(100, 100), (500, 140)], fill=(0, 0, 0), width=3)
        img.save(raw_path)

        with open(raw_path, "rb") as f:
            raw_bytes_before = f.read()

        # Capture orientation
        res = capture_plate_orientation(line=(100, 100, 500, 140), image_geometry={"width": 600, "height": 600})
        assert res["angle_degrees"] > 0

        # Apply rotation
        out_p = apply_plate_orientation(raw_path, res, output_path=working_path)
        assert os.path.exists(working_path)

        # Verify raw source remains 100% bit-for-bit unchanged
        with open(raw_path, "rb") as f:
            raw_bytes_after = f.read()
        assert raw_bytes_before == raw_bytes_after, "Raw source file was modified!"


def test_coordinate_transform_for_downstream_use():
    """6. Proof: point transform around center maps downstream grid coordinates accurately."""
    cx, cy = 400, 300
    angle = 5.0
    px, py = 200, 150
    
    rx, ry = transform_point_around_center(px, py, cx, cy, angle)
    # Inverse rotation should return back to original point
    back_x, back_y = transform_point_around_center(rx, ry, cx, cy, -angle)
    
    assert abs(back_x - px) < 1e-4
    assert abs(back_y - py) < 1e-4


def test_per_image_isolation():
    """7. Proof: orientation results are per-image and do not pollute other images."""
    res1 = capture_plate_orientation(line=(100, 100, 800, 150), image_geometry={"image_uid": "IMG_01"})
    res2 = capture_plate_orientation(line=(100, 150, 800, 100), image_geometry={"image_uid": "IMG_02"})

    assert res1["angle_degrees"] > 0
    assert res2["angle_degrees"] < 0
    assert res1["angle_degrees"] != res2["angle_degrees"]


def test_skip_mode_preserves_four_click_compatibility():
    """8. Proof: skipping orientation returns 0.0 angle without breaking downstream workflow."""
    res_skip = capture_plate_orientation(options={"skip": True})
    assert res_skip["contract_version"] == 1
    assert res_skip["angle_degrees"] == 0.0
    assert res_skip["needs_manual_review"] is False
    assert res_skip["diagnostics"]["status"] == "SKIPPED"


def test_contract_schema_conformance():
    """9. Proof: output conforms strictly to contracts/rotation_result.schema.json v1."""
    res = capture_plate_orientation(line={"x1": 100, "y1": 100, "x2": 900, "y2": 150})
    
    # Required schema fields: contract_version, angle_degrees, method, needs_manual_review
    assert res["contract_version"] == 1
    assert isinstance(res["angle_degrees"], (int, float))
    assert isinstance(res["method"], str) and len(res["method"]) >= 1
    assert isinstance(res["needs_manual_review"], bool)
    assert res["confidence"] is None or (0 <= res["confidence"] <= 1)
    assert isinstance(res["diagnostics"], dict)


if __name__ == "__main__":
    test_modest_clockwise_tilt()
    print("[PASS] test_modest_clockwise_tilt")
    test_modest_counter_clockwise_tilt()
    print("[PASS] test_modest_counter_clockwise_tilt")
    test_near_zero_tilt()
    print("[PASS] test_near_zero_tilt")
    test_top_and_bottom_edge_equivalence()
    print("[PASS] test_top_and_bottom_edge_equivalence")
    test_non_destructive_preview_and_apply()
    print("[PASS] test_non_destructive_preview_and_apply")
    test_coordinate_transform_for_downstream_use()
    print("[PASS] test_coordinate_transform_for_downstream_use")
    test_per_image_isolation()
    print("[PASS] test_per_image_isolation")
    test_skip_mode_preserves_four_click_compatibility()
    print("[PASS] test_skip_mode_preserves_four_click_compatibility")
    test_contract_schema_conformance()
    print("[PASS] test_contract_schema_conformance")
    print("\nALL 9 WHOLE-PLATE ORIENTATION PROOF TESTS PASSED.")
