from __future__ import annotations

from pathlib import Path

from tools.project_state import (
    new_project_state,
    record_crop,
    record_crop_export,
    record_derivative,
    record_grid_asset,
    record_orientation,
    validate_project_state,
)


def model() -> dict:
    return {
        "contract_version": 1,
        "sessions": [{"session_uid": "S1", "exp": "E", "date": "2026-08-24"}],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "S1",
                "image_number": 1,
                "original": "image1.jpg",
                "exp": "E",
                "set": "A",
            }
        ],
    }


def grid() -> dict:
    return {
        "asset_type": "GridCoordinateAsset",
        "status": "accepted",
        "asset_id": "g1",
        "coordinate_space": {"id": "source_image_pixels"},
    }


def test_record_crop_exports_by_tier_and_validate(tmp_path: Path) -> None:
    state = new_project_state(tmp_path, model())
    record_crop_export(
        state,
        "I1",
        "Unprocessed",
        {"status": "ACCEPTED", "output_path": "Crops/unprocessed.png"},
    )
    record_crop_export(
        state,
        "I1",
        "Processed",
        {
            "status": "ACCEPTED",
            "source_kind": "processed",
            "output_path": "Crops/processed.png",
        },
    )
    validate_project_state(state)
    assert state["images"]["I1"]["crop_exports"]["Unprocessed"]["status"] == "ACCEPTED"
    assert (
        state["images"]["I1"]["crop_exports"]["Processed"]["source_kind"] == "processed"
    )


def test_orientation_crop_and_grid_changes_stale_all_crop_exports(
    tmp_path: Path,
) -> None:
    state = new_project_state(tmp_path, model())
    record_crop_export(state, "I1", "Unprocessed", {"status": "ACCEPTED"})
    record_crop_export(
        state, "I1", "Processed", {"status": "ACCEPTED", "source_kind": "processed"}
    )
    record_orientation(state, "I1", {"status": "ACCEPTED", "angle_degrees": 1})
    assert all(
        v["status"] == "STALE" for v in state["images"]["I1"]["crop_exports"].values()
    )

    record_crop_export(state, "I1", "Unprocessed", {"status": "ACCEPTED"})
    record_crop_export(
        state, "I1", "Processed", {"status": "ACCEPTED", "source_kind": "processed"}
    )
    record_crop(state, "I1", {"status": "ACCEPTED", "crop_box": {"x": 1}})
    assert all(
        v["status"] == "STALE" for v in state["images"]["I1"]["crop_exports"].values()
    )

    record_crop_export(state, "I1", "Unprocessed", {"status": "ACCEPTED"})
    record_crop_export(
        state, "I1", "Processed", {"status": "ACCEPTED", "source_kind": "processed"}
    )
    record_grid_asset(state, "I1", grid(), tmp_path / "grid.json")
    assert all(
        v["status"] == "STALE" for v in state["images"]["I1"]["crop_exports"].values()
    )


def test_visibility_stales_processed_exports_and_annotation_only(
    tmp_path: Path,
) -> None:
    state = new_project_state(tmp_path, model())
    record_crop_export(
        state, "I1", "Unprocessed", {"status": "ACCEPTED", "source_kind": "working"}
    )
    record_crop_export(
        state, "I1", "Processed", {"status": "ACCEPTED", "source_kind": "processed"}
    )
    record_derivative(
        state, "I1", "annotation", {"status": "ACCEPTED", "output_path": "a.png"}
    )
    record_derivative(
        state, "I1", "visibility", {"status": "ACCEPTED", "output_path": "v.png"}
    )
    image = state["images"]["I1"]
    assert image["crop_exports"]["Unprocessed"]["status"] == "ACCEPTED"
    assert image["crop_exports"]["Processed"]["status"] == "STALE"
    assert image["annotation"]["status"] == "STALE"
    assert image["annotation"]["stale_reason"] == "visibility changed"


def test_crop_export_requires_accepted_nonempty_tier(tmp_path: Path) -> None:
    state = new_project_state(tmp_path, model())
    try:
        record_crop_export(state, "I1", "", {"status": "ACCEPTED"})
        raise AssertionError("empty tier should fail")
    except ValueError:
        pass
    try:
        record_crop_export(state, "I1", "Unprocessed", {"status": "SKIPPED"})
        raise AssertionError("non-accepted export should fail")
    except ValueError:
        pass
