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

from crop import (
    calibrate_crop_size,
    place_plate_crop,
    apply_plate_crop,
    transform_point_to_crop,
    transform_point_from_crop_to_source
)


def test_four_boundary_calibration_square_size():
    """1. Proof: 4 boundary points derive expected square side."""
    # Left at x=100, Right at x=2080 (w=1980)
    # Top at y=50, Bottom at y=2070 (h=2020)
    calib = calibrate_crop_size(
        left_pt=(100, 500),
        right_pt=(2080, 600),
        top_pt=(1000, 50),
        bottom_pt=(1100, 2070),
        increment=50
    )
    # raw_side = min(1980, 2020) = 1980 -> floor(1980 / 50) * 50 = 1950
    assert calib["side_pixels"] == 1950
    assert calib["is_square"] is True
    assert calib["contract_version"] == 1


def test_default_rounding_down_50_px():
    """2. Proof: square side rounds down to nearest 50 by default."""
    c1 = calibrate_crop_size((0, 0), (1999, 0), (0, 0), (0, 2000))
    assert c1["side_pixels"] == 1950

    c2 = calibrate_crop_size((0, 0), (2000, 0), (0, 0), (0, 2000))
    assert c2["side_pixels"] == 2000

    c3 = calibrate_crop_size((0, 0), (2049, 0), (0, 0), (0, 2049))
    assert c3["side_pixels"] == 2000


def test_configurable_rounding_increment():
    """3. Proof: configurable rounding increment works."""
    c_10 = calibrate_crop_size((0, 0), (1987, 0), (0, 0), (0, 1987), increment=10)
    assert c_10["side_pixels"] == 1980

    c_100 = calibrate_crop_size((0, 0), (1987, 0), (0, 0), (0, 1987), increment=100)
    assert c_100["side_pixels"] == 1900


def test_two_image_size_reuse_different_offsets():
    """4. Proof: second image reuses size calibration while producing different crop rectangle from left/top anchors."""
    calib = calibrate_crop_size((100, 0), (2050, 0), (0, 100), (0, 2050), increment=50, calibration_id="calib_shared")
    assert calib["side_pixels"] == 1950

    # Image 1 at offset (120, 80)
    res1 = place_plate_crop(calib, left_edge_pt=(120, 900), top_edge_pt=(800, 80), options={"image_uid": "IMG_01"})
    assert res1["crop_box"]["x"] == 120
    assert res1["crop_box"]["y"] == 80
    assert res1["crop_box"]["width"] == 1950

    # Image 2 shifted at offset (210, 150)
    res2 = place_plate_crop(calib, left_edge_pt=(210, 400), top_edge_pt=(500, 150), options={"image_uid": "IMG_02"})
    assert res2["crop_box"]["x"] == 210
    assert res2["crop_box"]["y"] == 150
    assert res2["crop_box"]["width"] == 1950

    assert res1["crop_box"] != res2["crop_box"]


def test_exact_corners_not_required():
    """5. Proof: left-edge and top-edge points need not be the top-left corner."""
    calib = {"side_pixels": 1000, "calibration_id": "c1"}
    # Left edge clicked near bottom-left (x=50, y=900)
    # Top edge clicked near top-right (x=800, y=30)
    res = place_plate_crop(calib, left_edge_pt=(50, 900), top_edge_pt=(800, 30))
    assert res["crop_box"]["x"] == 50
    assert res["crop_box"]["y"] == 30
    assert res["crop_box"]["width"] == 1000
    assert res["crop_box"]["height"] == 1000


def test_non_destructive_preview_and_apply():
    """6. Proof: raw image is untouched, cropped output written correctly."""
    if not PIL_AVAILABLE:
        print("Skipping PIL test (Pillow not installed)")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_p = os.path.join(tmp_dir, "source.png")
        out_p = os.path.join(tmp_dir, "cropped.png")

        img = Image.new("RGB", (1000, 1000), color=(200, 200, 200))
        img.save(raw_p)

        with open(raw_p, "rb") as f:
            raw_bytes_before = f.read()

        calib = {"side_pixels": 400, "calibration_id": "c1"}
        res = place_plate_crop(calib, left_edge_pt=(100, 300), top_edge_pt=(400, 100))
        apply_plate_crop(raw_p, res, output_path=out_p)

        assert os.path.exists(out_p)
        with Image.open(out_p) as c_img:
            assert c_img.size == (400, 400)

        with open(raw_p, "rb") as f:
            raw_bytes_after = f.read()
        assert raw_bytes_before == raw_bytes_after


def test_retry_placement_preserves_calibration():
    """7. Proof: retrying placement does not mutate size calibration."""
    calib = {"side_pixels": 1200, "calibration_id": "calib_v1"}
    res1 = place_plate_crop(calib, (100, 200), (300, 50))
    res2 = place_plate_crop(calib, (120, 250), (320, 70))

    assert calib["side_pixels"] == 1200
    assert res1["crop_box"]["x"] == 100
    assert res2["crop_box"]["x"] == 120


def test_recalibration_replaces_size():
    """8. Proof: recalibration produces an updated calibration version."""
    calib_v1 = calibrate_crop_size((0, 0), (1000, 0), (0, 0), (0, 1000), calibration_id="c_v1")
    calib_v2 = calibrate_crop_size((0, 0), (1200, 0), (0, 0), (0, 1200), calibration_id="c_v2")

    assert calib_v1["side_pixels"] == 1000
    assert calib_v2["side_pixels"] == 1200


def test_crop_size_and_per_image_state_distinction():
    """9. Proof: crop size calibration and per-image crop result structures are decoupled."""
    calib = calibrate_crop_size((0, 0), (800, 0), (0, 0), (0, 800))
    res = place_plate_crop(calib, (50, 100), (100, 40), options={"image_uid": "IMG_X"})

    assert "crop_box" not in calib
    assert "measured_extents" not in res
    assert res["calibration_id"] == calib["calibration_id"]


def test_coordinate_transforms():
    """10. Proof: transform_point_to_crop and transform_point_from_crop_to_source are invertible."""
    calib = {"side_pixels": 500, "calibration_id": "c1"}
    res = place_plate_crop(calib, left_edge_pt=(150, 400), top_edge_pt=(400, 200))
    
    # Source spot at (350, 450)
    cx, cy = transform_point_to_crop(350, 450, res)
    assert cx == 350 - 150  # 200
    assert cy == 450 - 200  # 250

    orig_x, orig_y = transform_point_from_crop_to_source(cx, cy, res)
    assert orig_x == 350
    assert orig_y == 450


def test_skip_mode_preserves_four_click_route():
    """11. Proof: skipping crop preprocessing returns SKIPPED status without breaking flow."""
    calib = {"side_pixels": 1000, "calibration_id": "c1"}
    res = place_plate_crop(calib, (0, 0), (0, 0), options={"skip": True, "image_uid": "IMG_SKIP"})

    assert res["contract_version"] == 1
    assert res["status"] == "SKIPPED"
    assert res["crop_box"] is None
    assert res["needs_manual_review"] is False


def test_invalid_and_edge_inputs_fail_clearly():
    """12. Proof: invalid bounds or non-positive dimensions raise ValueError."""
    try:
        calibrate_crop_size((100, 0), (100, 0), (0, 0), (0, 100))
        assert False, "Should raise ValueError for 0 width"
    except ValueError as e:
        assert "Invalid boundary points" in str(e)

    try:
        calibrate_crop_size((0, 0), (100, 0), (0, 0), (0, 100), increment=0)
        assert False, "Should raise ValueError for invalid increment"
    except ValueError as e:
        assert "positive integer" in str(e)


if __name__ == "__main__":
    test_four_boundary_calibration_square_size()
    print("[PASS] test_four_boundary_calibration_square_size")
    test_default_rounding_down_50_px()
    print("[PASS] test_default_rounding_down_50_px")
    test_configurable_rounding_increment()
    print("[PASS] test_configurable_rounding_increment")
    test_two_image_size_reuse_different_offsets()
    print("[PASS] test_two_image_size_reuse_different_offsets")
    test_exact_corners_not_required()
    print("[PASS] test_exact_corners_not_required")
    test_non_destructive_preview_and_apply()
    print("[PASS] test_non_destructive_preview_and_apply")
    test_retry_placement_preserves_calibration()
    print("[PASS] test_retry_placement_preserves_calibration")
    test_recalibration_replaces_size()
    print("[PASS] test_recalibration_replaces_size")
    test_crop_size_and_per_image_state_distinction()
    print("[PASS] test_crop_size_and_per_image_state_distinction")
    test_coordinate_transforms()
    print("[PASS] test_coordinate_transforms")
    test_skip_mode_preserves_four_click_route()
    print("[PASS] test_skip_mode_preserves_four_click_route")
    test_invalid_and_edge_inputs_fail_clearly()
    print("[PASS] test_invalid_and_edge_inputs_fail_clearly")
    print("\nALL 12 PLATE CROP PREPROCESSING PROOF TESTS PASSED.")
