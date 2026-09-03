from __future__ import annotations

import json
from pathlib import Path

from tools.project_state import (
    load_project_state,
    new_project_state,
    record_crop,
    record_crop_calibration,
    record_derivative,
    record_grid_asset,
    record_orientation,
    record_matrix_export,
    record_setup_result,
    save_project_state,
    select_crop_calibration,
)


def project_model() -> dict:
    return {
        "contract_version": 1,
        "sessions": [{"session_uid": "S1", "exp": "E1", "date": "2026-08-24"}],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "S1",
                "image_number": 1,
                "original": "image1.jpg",
                "working_filename": "working1.jpg",
                "exp": "E1",
                "set": "A",
                "annotation_set": "L1",
            }
        ],
        "layouts": {},
        "diagnostics": [],
    }


def orientation(angle: float = 1.5) -> dict:
    return {
        "status": "ACCEPTED",
        "angle_degrees": angle,
        "output_path": "Working/I1.jpg",
    }


def crop(x: int = 10) -> dict:
    return {
        "status": "ACCEPTED",
        "crop_box": {"x": x, "y": 20, "width": 100, "height": 100},
        "output_path": "Working/I1.crop.jpg",
    }


def grid() -> dict:
    return {
        "asset_type": "GridCoordinateAsset",
        "status": "accepted",
        "asset_id": "grid-I1",
        "coordinate_space": {"id": "source_image_pixels"},
    }


def test_state_persists_uid_paths_and_assets_atomically(tmp_path: Path) -> None:
    state = new_project_state(tmp_path, project_model())
    record_setup_result(
        state,
        {
            "images": [
                {
                    "image_uid": "I1",
                    "raw_path": "Raw/session/image1.jpg",
                    "working_path": "Working/working1.jpg",
                    "disposition": "COPIED_RENAMED",
                }
            ],
            "summary": {"total_expected": 1},
            "conversion_map_path": "Metadata/image_name_conversions.txt",
        },
    )
    record_crop_calibration(
        state,
        {"calibration_id": "C1", "side_pixels": 100, "contract_version": 1},
    )
    record_orientation(state, "I1", orientation())
    record_crop(state, "I1", crop())
    record_grid_asset(state, "I1", grid(), tmp_path / "GridCoordinates" / "I1.json")
    record_derivative(
        state,
        "I1",
        "visibility",
        {"status": "ACCEPTED", "output_path": "Processed/I1.png"},
    )
    record_derivative(
        state,
        "I1",
        "annotation",
        {"status": "ACCEPTED", "output_path": "Annotated/I1.png"},
    )

    path = save_project_state(state)
    loaded = load_project_state(tmp_path)
    assert path == tmp_path / "z. Metadata" / "State" / "workflow_project.json"
    assert loaded["images"]["I1"]["working_path"] == "Working/working1.jpg"
    assert loaded["images"]["I1"]["grid"]["asset_id"] == "grid-I1"
    assert loaded["crop_calibrations"]["C1"]["side_pixels"] == 100
    assert loaded["active_crop_calibration_id"] == "C1"
    assert not list(path.parent.glob("*.tmp"))


def test_active_crop_calibration_survives_sorted_save_and_legacy_load(
    tmp_path: Path,
) -> None:
    state = new_project_state(tmp_path, project_model())
    assert state["active_crop_calibration_id"] is None
    record_crop_calibration(
        state, {"calibration_id": "Z-first", "side_pixels": 1700}
    )
    record_crop_calibration(
        state, {"calibration_id": "A-second", "side_pixels": 1750}
    )
    assert state["active_crop_calibration_id"] == "A-second"
    select_crop_calibration(state, "Z-first")
    save_project_state(state)
    assert load_project_state(tmp_path)["active_crop_calibration_id"] == "Z-first"
    try:
        select_crop_calibration(state, "missing")
    except ValueError as exc:
        assert "Unknown crop calibration" in str(exc)
    else:
        raise AssertionError("Unknown calibration selection should fail")

    path = save_project_state(state)
    legacy = json.loads(path.read_text(encoding="utf-8"))
    legacy.pop("active_crop_calibration_id")
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert load_project_state(tmp_path)["active_crop_calibration_id"] in {
        "A-second",
        "Z-first",
    }


def test_geometry_changes_mark_only_true_downstream_assets_stale(
    tmp_path: Path,
) -> None:
    state = new_project_state(tmp_path, project_model())
    record_orientation(state, "I1", orientation())
    record_crop(state, "I1", crop())
    record_grid_asset(state, "I1", grid(), tmp_path / "grid.json")
    record_derivative(state, "I1", "visibility", {"status": "ACCEPTED"})
    record_derivative(state, "I1", "annotation", {"status": "ACCEPTED"})

    record_grid_asset(state, "I1", grid(), tmp_path / "grid.json")
    assert state["images"]["I1"]["visibility"]["status"] == "ACCEPTED"

    record_orientation(state, "I1", orientation(2.0))
    image = state["images"]["I1"]
    assert image["crop"]["status"] == "STALE"
    assert image["grid"]["status"] == "STALE"
    assert image["visibility"]["status"] == "STALE"
    assert image["annotation"]["status"] == "STALE"
    assert image["crop"]["stale_reason"] == "orientation changed"


def test_grid_geometry_digest_controls_staleness_and_matrix_dependencies(
    tmp_path: Path,
) -> None:
    state = new_project_state(tmp_path, project_model())
    first = grid()
    first["geometry_sha256"] = "a" * 64
    record_grid_asset(state, "I1", first, tmp_path / "first.grid.json")
    record_derivative(state, "I1", "visibility", {"status": "ACCEPTED"})
    record_matrix_export(
        state,
        {
            "status": "ACCEPTED",
            "request_id": "matrix-1",
            "items": [{"image_uid": "I1"}],
        },
    )

    identical = dict(first, asset_id="renamed-asset")
    record_grid_asset(state, "I1", identical, tmp_path / "moved.grid.json")
    assert state["images"]["I1"]["visibility"]["status"] == "ACCEPTED"
    assert state["matrix_exports"]["matrix-1"]["status"] == "ACCEPTED"

    changed = dict(first, geometry_sha256="b" * 64)
    record_grid_asset(state, "I1", changed, tmp_path / "changed.grid.json")
    assert state["images"]["I1"]["visibility"]["status"] == "STALE"
    assert state["matrix_exports"]["matrix-1"]["status"] == "STALE"
    assert "grid changed for I1" in state["matrix_exports"]["matrix-1"]["stale_reason"]
