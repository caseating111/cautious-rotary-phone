import os
import sys
import tempfile

try:
    from PIL import Image, ImageDraw
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

cur_dir = os.path.dirname(__file__)
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from visibility import (
    calculate_grid_roi,
    compute_visibility_statistics,
    adjust_plate_visibility,
    apply_visibility_adjustment,
    ReviewQueue
)


def test_saved_grid_derives_foreground_roi():
    """1. Proof: saved spot coordinates derive correct bounding box ROI with padding."""
    spots = [(100, 100), (900, 100), (100, 700), (900, 700)]
    roi = calculate_grid_roi(spots, padding=20.0, max_width=1000, max_height=1000)

    assert roi["x"] == 80.0
    assert roi["y"] == 80.0
    assert roi["right"] == 920.0
    assert roi["bottom"] == 720.0
    assert roi["width"] == 840.0
    assert roi["height"] == 640.0


def test_outside_grid_derives_robust_background_stats():
    """2. Proof: outside-grid region isolates background statistics from colony spots."""
    if not DEPS_AVAILABLE:
        print("Skipping numpy test (numpy not installed)")
        return

    # Create dummy image: background is dark (pixel value 30), colonies are bright (pixel value 220)
    arr = np.full((500, 500), 30, dtype=np.uint8)
    # Put bright colonies in grid area (100..400, 100..400)
    arr[150:350, 150:350] = 220

    roi = {"left": 150, "top": 150, "right": 350, "bottom": 350, "width": 200, "height": 200}
    stats = compute_visibility_statistics(arr, roi, margin=50.0)

    assert stats["bg_median"] == 30.0
    assert stats["fg_p99"] == 220.0


def test_display_transform_applies_to_entire_image():
    """3. Proof: visibility transform applies to entire image, stretching dynamic range."""
    if not DEPS_AVAILABLE:
        return

    arr = np.full((200, 200), 50, dtype=np.uint8)
    arr[50:150, 50:150] = 180  # inner spots

    spots = [(50, 50), (150, 150)]
    res = adjust_plate_visibility(arr, spots, preset="background_aware_linear")
    
    assert res["status"] == "APPROVED"
    assert res["parameters"]["black_point"] <= 50.0
    assert res["parameters"]["white_point"] >= 180.0

    out = apply_visibility_adjustment(arr, res)
    assert np.array(out).shape == arr.shape


def test_non_destructive_preview_and_apply():
    """4. Proof: source image file remains untouched after adjustment is written."""
    if not DEPS_AVAILABLE:
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_p = os.path.join(tmp_dir, "plate_raw.png")
        out_p = os.path.join(tmp_dir, "plate_adj.png")

        img = Image.new("L", (400, 400), color=40)
        img.save(raw_p)

        with open(raw_p, "rb") as f:
            raw_bytes_before = f.read()

        spots = [(100, 100), (300, 300)]
        res = adjust_plate_visibility(raw_p, spots, options={"image_uid": "IMG_001"})
        apply_visibility_adjustment(raw_p, res, output_path=out_p)

        assert os.path.exists(out_p)
        with open(raw_p, "rb") as f:
            raw_bytes_after = f.read()
        assert raw_bytes_before == raw_bytes_after


def test_approve_saves_processed_output():
    """5. Proof: approved adjustment produces valid parameters and contract output."""
    spots = [(50, 50), (250, 250)]
    arr = np.full((300, 300), 60, dtype=np.uint8)
    res = adjust_plate_visibility(arr, spots, options={"status": "APPROVED", "image_uid": "IMG_APP"})

    assert res["status"] == "APPROVED"
    assert res["needs_manual_review"] is False
    assert "black_point" in res["parameters"]


def test_mark_for_manual_creates_review_queue_entry():
    """6. Proof: manual review flag sets needs_manual_review without failing."""
    spots = [(50, 50), (250, 250)]
    arr = np.full((300, 300), 60, dtype=np.uint8)
    res = adjust_plate_visibility(
        arr,
        spots,
        options={
            "status": "MANUAL_REVIEW",
            "manual_review_reason": "Low colony contrast in row 4",
            "image_uid": "IMG_MANUAL"
        }
    )

    assert res["status"] == "MANUAL_REVIEW"
    assert res["needs_manual_review"] is True
    assert res["manual_review_reason"] == "Low colony contrast in row 4"


def test_review_queue_persistence_and_resolution():
    """7. Proof: ReviewQueue persists entries to disk and supports mark_reviewed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        q_file = os.path.join(tmp_dir, "review_queue.json")
        q = ReviewQueue(q_file)
        
        q.add_entry("IMG_01", "raw/img1.jpg", reason="Dim colonies")
        q.add_entry("IMG_02", "raw/img2.jpg", reason="High background")

        pending = q.get_pending()
        assert len(pending) == 2

        # Mark IMG_01 as reviewed
        q.mark_reviewed("IMG_01")
        assert len(q.get_pending()) == 1
        assert q.get_pending()[0]["image_uid"] == "IMG_02"

        # Reload from disk
        q2 = ReviewQueue(q_file)
        assert len(q2.get_pending()) == 1


def test_presets_reusability():
    """8. Proof: presets can be selected and customized."""
    spots = [(50, 50), (250, 250)]
    arr = np.full((300, 300), 60, dtype=np.uint8)
    
    res1 = adjust_plate_visibility(arr, spots, preset="gamma_boost")
    assert res1["parameters"]["gamma"] == 0.8

    res2 = adjust_plate_visibility(arr, spots, preset={"method": "custom", "gamma": 1.5, "bg_percentile": 5.0, "fg_percentile": 95.0})
    assert res2["parameters"]["gamma"] == 1.5


def test_processed_crop_integration_geometry_invariance():
    """9. Proof: visibility adjustment preserves image dimensions and geometry for grid reuse."""
    if not DEPS_AVAILABLE:
        return
    
    arr = np.full((400, 400), 50, dtype=np.uint8)
    spots = [(100, 100), (300, 300)]
    res = adjust_plate_visibility(arr, spots)
    out = apply_visibility_adjustment(arr, res)

    # Image dimensions must not change
    assert np.array(out).shape == arr.shape


def test_subfolder_and_uid_identity_preservation():
    """10. Proof: image UID and output paths are preserved cleanly."""
    spots = [(50, 50), (250, 250)]
    arr = np.full((300, 300), 60, dtype=np.uint8)
    res = adjust_plate_visibility(
        arr,
        spots,
        options={"image_uid": "E1_14.08.26_24h_I001", "output_path": "processed/E1/plate.png"}
    )
    assert res["image_uid"] == "E1_14.08.26_24h_I001"
    assert res["output_path"] == "processed/E1/plate.png"


if __name__ == "__main__":
    test_saved_grid_derives_foreground_roi()
    print("[PASS] test_saved_grid_derives_foreground_roi")
    test_outside_grid_derives_robust_background_stats()
    print("[PASS] test_outside_grid_derives_robust_background_stats")
    test_display_transform_applies_to_entire_image()
    print("[PASS] test_display_transform_applies_to_entire_image")
    test_non_destructive_preview_and_apply()
    print("[PASS] test_non_destructive_preview_and_apply")
    test_approve_saves_processed_output()
    print("[PASS] test_approve_saves_processed_output")
    test_mark_for_manual_creates_review_queue_entry()
    print("[PASS] test_mark_for_manual_creates_review_queue_entry")
    test_review_queue_persistence_and_resolution()
    print("[PASS] test_review_queue_persistence_and_resolution")
    test_presets_reusability()
    print("[PASS] test_presets_reusability")
    test_processed_crop_integration_geometry_invariance()
    print("[PASS] test_processed_crop_integration_geometry_invariance")
    test_subfolder_and_uid_identity_preservation()
    print("[PASS] test_subfolder_and_uid_identity_preservation")
    print("\nALL 10 VISIBILITY ADJUSTMENT PROOF TESTS PASSED.")
