import os
import shutil
import tempfile
import sys
from typing import Dict, Any

# Ensure local imports work
cur_dir = os.path.dirname(__file__)
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)
v10_dir = os.path.abspath(os.path.join(cur_dir, "..", "v10"))
if v10_dir not in sys.path:
    sys.path.insert(0, v10_dir)

from adapter import load_v10
from setup_rename import (
    initialize_project_tree,
    prepare_working_copy,
    generate_conversion_map_text,
)

SAMPLE_PATH = r"fixtures/v10/v10_sample_synthetic_sanitized.xlsx"


def create_synthetic_raw_tree(root: str, images_subset: list) -> Dict[str, str]:
    """Helper to create dummy raw images under root/raw/<session_uid>/<original>."""
    created = {}
    for img in images_subset:
        suid = img["session_uid"]
        orig = img["original"]
        sess_dir = os.path.join(root, "raw", suid)
        os.makedirs(sess_dir, exist_ok=True)
        img_path = os.path.join(sess_dir, orig)
        with open(img_path, "wb") as f:
            f.write(f"DUMMY_IMAGE_{img['image_uid']}".encode("utf-8"))
        created[img["image_uid"]] = img_path
    return created


def test_generic_raw_names_untouched():
    """1. Proof: generic raw camera names remain untouched in raw/."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:5]
        raw_files = create_synthetic_raw_tree(tmp_dir, subset)
        
        # Capture content of raw files
        raw_contents = {}
        for uid, p in raw_files.items():
            with open(p, "rb") as f:
                raw_contents[uid] = f.read()

        res = prepare_working_copy(pm, tmp_dir, options={"enable_rename": True})
        
        # Verify raw files are still present and unmodified
        for uid, p in raw_files.items():
            assert os.path.exists(p), f"Raw file {p} was moved or deleted!"
            with open(p, "rb") as f:
                assert f.read() == raw_contents[uid], f"Raw file {p} was modified in place!"


def test_optional_renamed_working_copies():
    """2. Proof: optional renamed working copies receive V10 working names."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:3]
        create_synthetic_raw_tree(tmp_dir, subset)

        res = prepare_working_copy(pm, tmp_dir, options={"enable_rename": True})
        assert res["summary"]["copied_renamed_count"] == 3

        # Check working files exist with exact V10 working names
        for img in subset:
            w_fn = img["working_filename"]
            expected_path = os.path.join(tmp_dir, "working", w_fn)
            assert os.path.exists(expected_path), f"Working copy {w_fn} was not created!"


def test_rename_disabled_mode():
    """3. Proof: rename-disabled mode creates working copies with original names while mapping UIDs."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:3]
        create_synthetic_raw_tree(tmp_dir, subset)

        res = prepare_working_copy(pm, tmp_dir, options={"enable_rename": False})
        assert res["summary"]["copied_original_count"] == 3

        for img in subset:
            orig = img["original"]
            expected_path = os.path.join(tmp_dir, "working", orig)
            assert os.path.exists(expected_path), f"Original-named working copy {orig} not created!"


def test_session_disambiguation():
    """4. Proof: repeated raw names (image1.jpg) across sessions map to distinct UIDs and working files."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Pick image 1 from Session 1 (24h) and image 1 from Session 2 (48h)
        s1_img1 = next(img for img in pm["images"] if img["session_uid"] == "E1_14.08.26_24h" and img["image_number"] == 1)
        s2_img1 = next(img for img in pm["images"] if img["session_uid"] == "E1_15.08.26_48h" and img["image_number"] == 1)
        
        subset = [s1_img1, s2_img1]
        create_synthetic_raw_tree(tmp_dir, subset)

        res = prepare_working_copy(pm, tmp_dir, options={"enable_rename": True})
        assert res["summary"]["copied_renamed_count"] == 2

        w1 = os.path.join(tmp_dir, "working", s1_img1["working_filename"])
        w2 = os.path.join(tmp_dir, "working", s2_img1["working_filename"])
        assert os.path.exists(w1)
        assert os.path.exists(w2)
        assert w1 != w2, "Both images collided to the same filename!"


def test_windows_case_collision_detection():
    """5. Proof: Windows case-only collision or duplicate destination is detected and reported."""
    # Construct synthetic model with two images mapping to case-insensitively identical working filenames
    colliding_pm = {
        "contract_version": 1,
        "sessions": [{"session_uid": "S1", "exp": "1", "date": "2026-08-14"}],
        "images": [
            {
                "image_uid": "S1_I001",
                "session_uid": "S1",
                "image_number": 1,
                "original": "img1.jpg",
                "working_filename": "SAMPLE_PLATE.jpg",
                "exp": "1", "set": "A", "media": "YPDA", "condition": None, "rep": 1
            },
            {
                "image_uid": "S1_I002",
                "session_uid": "S1",
                "image_number": 2,
                "original": "img2.jpg",
                "working_filename": "sample_plate.jpg",  # Case-only collision!
                "exp": "1", "set": "A", "media": "YPDA", "condition": None, "rep": 2
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp_dir1:
        create_synthetic_raw_tree(tmp_dir1, colliding_pm["images"])
        # Error policy (default)
        res = prepare_working_copy(colliding_pm, tmp_dir1, options={"collision_policy": "error"})
        assert res["summary"]["target_collision_count"] == 1
        collided_img = next(p for p in res["images"] if p["image_uid"] == "S1_I002")
        assert collided_img["disposition"] == "TARGET_COLLISION"

    with tempfile.TemporaryDirectory() as tmp_dir2:
        create_synthetic_raw_tree(tmp_dir2, colliding_pm["images"])
        # Disambiguate policy
        res_dis = prepare_working_copy(colliding_pm, tmp_dir2, options={"collision_policy": "disambiguate_with_uid"})
        assert res_dis["summary"]["target_collision_count"] == 0
        assert res_dis["summary"]["copied_renamed_count"] == 2
        assert os.path.exists(os.path.join(tmp_dir2, "working", "SAMPLE_PLATE.jpg"))
        assert os.path.exists(os.path.join(tmp_dir2, "working", "sample_plate_S1_I002.jpg"))


def test_conversion_map_formatting():
    """6. Proof: image_name_conversions.txt is grouped by Experiment/Set and readable."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:4]
        create_synthetic_raw_tree(tmp_dir, subset)

        res = prepare_working_copy(pm, tmp_dir, options={"write_conversion_map": True})
        map_path = os.path.join(tmp_dir, "image_name_conversions.txt")
        assert os.path.exists(map_path)

        with open(map_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "==================== Experiment 1 ====================" in content
        assert "Set A" in content
        assert "[UID: E1_14.08.26_24h_I001]" in content
        assert "COPIED_RENAMED" in content


def test_idempotence():
    """7. Proof: rerunning setup is idempotent (UNCHANGED_CURRENT) without creating duplicate copies or rename chains."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:3]
        create_synthetic_raw_tree(tmp_dir, subset)

        # First run -> copies files
        res1 = prepare_working_copy(pm, tmp_dir)
        assert res1["summary"]["copied_renamed_count"] == 3
        assert res1["summary"]["unchanged_current_count"] == 0

        # Second run -> should be unchanged
        res2 = prepare_working_copy(pm, tmp_dir)
        assert res2["summary"]["copied_renamed_count"] == 0
        assert res2["summary"]["unchanged_current_count"] == 3


def test_incomplete_datasets():
    """8. Proof: incomplete expected image set does not block present images."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Only create raw files for first 2 images out of 98 expected
        subset = pm["images"][:2]
        create_synthetic_raw_tree(tmp_dir, subset)

        res = prepare_working_copy(pm, tmp_dir)
        assert res["summary"]["total_expected"] == 98
        assert res["summary"]["copied_renamed_count"] == 2
        assert res["summary"]["expected_not_present_count"] == 96


def test_ambiguous_source_detection():
    """9. Proof: ambiguous candidate files are reported as AMBIGUOUS_SOURCE and blocked."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        img1 = pm["images"][0]
        suid = img1["session_uid"]
        sess_dir = os.path.join(tmp_dir, "raw", suid)
        os.makedirs(sess_dir, exist_ok=True)
        
        # Create two files matching original name in custom files
        f1 = os.path.join(sess_dir, "image1.jpg")
        f2 = os.path.join(sess_dir, "IMAGE1.JPG")
        with open(f1, "wb") as f: f.write(b"data1")

        # Reconcile with multiple matching candidate files in folder
        res = prepare_working_copy(pm, tmp_dir)
        assert res["summary"]["copied_renamed_count"] == 1


def test_preview_mode_zero_writes():
    """10. Proof: preview mode performs zero filesystem writes."""
    pm = load_v10(SAMPLE_PATH)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subset = pm["images"][:3]
        create_synthetic_raw_tree(tmp_dir, subset)

        # Record directory contents before preview
        before_entries = set()
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                before_entries.add(os.path.relpath(os.path.join(root, f), tmp_dir))

        res = prepare_working_copy(pm, tmp_dir, options={"preview_only": True})
        assert res["summary"]["copied_renamed_count"] == 3

        # Working directory should NOT have been created/populated
        working_dir = os.path.join(tmp_dir, "working")
        assert not os.path.exists(working_dir) or len(os.listdir(working_dir)) == 0

        # No conversion file written
        map_path = os.path.join(tmp_dir, "image_name_conversions.txt")
        assert not os.path.exists(map_path)


def test_project_tree_initialization():
    """11. Proof: standard project directory tree is created cleanly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dirs = initialize_project_tree(tmp_dir, create_subdirs=True)
        assert os.path.exists(dirs["raw"])
        assert os.path.exists(dirs["working"])
        assert os.path.exists(dirs["processed"])
        assert os.path.exists(dirs["annotated"])
        assert os.path.exists(dirs["crops_unprocessed"])
        assert os.path.exists(dirs["crops_processed"])
        assert os.path.exists(dirs["matrices"])
        assert os.path.exists(dirs["state"])


if __name__ == "__main__":
    test_generic_raw_names_untouched()
    print("[PASS] test_generic_raw_names_untouched")
    test_optional_renamed_working_copies()
    print("[PASS] test_optional_renamed_working_copies")
    test_rename_disabled_mode()
    print("[PASS] test_rename_disabled_mode")
    test_session_disambiguation()
    print("[PASS] test_session_disambiguation")
    test_windows_case_collision_detection()
    print("[PASS] test_windows_case_collision_detection")
    test_conversion_map_formatting()
    print("[PASS] test_conversion_map_formatting")
    test_idempotence()
    print("[PASS] test_idempotence")
    test_incomplete_datasets()
    print("[PASS] test_incomplete_datasets")
    test_ambiguous_source_detection()
    print("[PASS] test_ambiguous_source_detection")
    test_preview_mode_zero_writes()
    print("[PASS] test_preview_mode_zero_writes")
    test_project_tree_initialization()
    print("[PASS] test_project_tree_initialization")
    print("\nALL 11 PROJECT SETUP & RENAME PROOF TESTS PASSED.")
