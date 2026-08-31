from __future__ import annotations

from pathlib import Path

from tools.applets.culture_crop_export import culture_crop_signature
from tools.project_state import (
    load_project_state,
    new_project_state,
    record_crop,
    record_crop_export,
    record_culture_status,
    record_derivative,
    record_derivative_transition,
    record_grid_asset,
    record_orientation,
    save_project_state,
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


def test_culture_status_persists_without_replacing_exports(tmp_path: Path) -> None:
    state = new_project_state(tmp_path, model())
    record_crop_export(state, "I1", "Unprocessed", {"status": "ACCEPTED"})
    signature = culture_crop_signature(
        tier="Unprocessed",
        source_kind="cropped",
        states=("Top", "Low"),
        columns=None,
        crop_width=130,
        crop_height=546,
    )
    record_culture_status(state, "I1", "SKIPPED", signature)
    save_project_state(state)
    reopened = load_project_state(tmp_path)
    image = reopened["images"]["I1"]
    assert image["culture"]["status"] == "SKIPPED"
    assert image["culture"]["signature"] == signature
    assert image["crop_exports"]["Unprocessed"]["status"] == "ACCEPTED"


def test_culture_status_stales_with_its_actual_sources(tmp_path: Path) -> None:
    state = new_project_state(tmp_path, model())
    unprocessed = culture_crop_signature(
        tier="Unprocessed",
        source_kind="cropped",
        states=("Top",),
        columns=None,
        crop_width=130,
        crop_height=546,
    )
    record_culture_status(state, "I1", "SKIPPED", unprocessed)
    record_orientation(state, "I1", {"status": "ACCEPTED", "angle_degrees": 1})
    assert state["images"]["I1"]["culture"]["status"] == "STALE"

    processed = culture_crop_signature(
        tier="Processed",
        source_kind="processed",
        states=("Top",),
        columns=None,
        crop_width=130,
        crop_height=546,
    )
    record_culture_status(state, "I1", "ACCEPTED", processed)
    record_derivative(
        state, "I1", "visibility", {"status": "ACCEPTED", "output_path": "v.png"}
    )
    assert state["images"]["I1"]["culture"]["status"] == "STALE"
    assert state["images"]["I1"]["culture"]["stale_reason"] == "visibility changed"


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


def test_visibility_skip_and_review_also_stale_processed_dependents(
    tmp_path: Path,
) -> None:
    for status in ("SKIPPED", "MANUAL_REVIEW"):
        state = new_project_state(tmp_path / status, model())
        record_crop_export(
            state, "I1", "Unprocessed", {"status": "ACCEPTED", "source_kind": "working"}
        )
        record_crop_export(
            state, "I1", "Processed", {"status": "ACCEPTED", "source_kind": "processed"}
        )
        record_derivative(state, "I1", "visibility", {"status": "ACCEPTED"})
        record_derivative(state, "I1", "annotation", {"status": "ACCEPTED"})
        record_derivative_transition(
            state, "I1", "visibility", {"status": status}
        )
        image = state["images"]["I1"]
        assert image["visibility"]["status"] == status
        assert image["annotation"]["status"] == "STALE"
        assert image["crop_exports"]["Processed"]["status"] == "STALE"
        assert image["crop_exports"]["Unprocessed"]["status"] == "ACCEPTED"


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
