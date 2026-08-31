from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tools.applet_workflows import ProjectWorkflow
from tools.grid_coordinates import build_grid_coordinate_asset


def _asset() -> dict:
    refs = {
        "r1c1": {"x": 80, "y": 180},
        "r1clast": {"x": 220, "y": 180},
        "r5c1": {"x": 80, "y": 300},
        "r5clast": {"x": 220, "y": 300},
    }
    return build_grid_coordinate_asset(
        image_ref="session/plate.png",
        image_width=300,
        image_height=700,
        grid_rows=8,
        grid_cols=10,
        reference_points=refs,
        image_uid="img-1",
    )


def _layout() -> dict:
    labels = lambda prefix: [{"pos": c, "label": f"{prefix}{c}"} for c in range(1, 11)]
    return {
        "contract_version": 1,
        "layout_id": "L1",
        "grid_rows": 8,
        "grid_cols": 10,
        "vertical_labels": [{"pos": r, "label": f"R{r}"} for r in range(1, 9)],
        "strain_bands": [
            {"order": 1, "row_start": 1, "row_end": 4, "labels": labels("A")},
            {"order": 2, "row_start": 5, "row_end": 8, "labels": labels("B")},
        ],
    }


def _workflow(tmp_path: Path, source: Path) -> ProjectWorkflow:
    workflow = object.__new__(ProjectWorkflow)
    workflow.state = {
        "contract_version": 1,
        "asset_type": "WorkflowProjectState",
        "project_root": str(tmp_path),
        "project_model": {
            "contract_version": 1,
            "sessions": [{"session_uid": "S1", "date": "2026-08-24"}],
            "images": [{"image_uid": "img-1"}],
        },
        "crop_calibrations": {},
        "images": {"img-1": {"image_uid": "img-1", "visibility": {}}},
        "updated_at": "2026-08-24T00:00:00+00:00",
    }
    workflow._model_image = lambda _uid: {
        "image_uid": "img-1",
        "session_uid": "S1",
        "exp": "E/1",
        "set": "S 1",
        "condition": "YPDA",
    }
    workflow.grid_asset = lambda _uid: _asset()
    workflow._plate_layout = lambda _uid: _layout()
    workflow.source_for = lambda _uid: source
    workflow._assert_grid_matches_source = lambda *_args: None
    workflow.save = lambda: tmp_path / "state.json"
    return workflow


def test_preview_uses_collision_safe_context_and_uid_root(tmp_path: Path) -> None:
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    plan = _workflow(tmp_path, source).preview_culture_crop_export(
        "img-1",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    assert plan["status"] == "PROPOSED"
    assert str(Path("Crops") / "Unprocessed") in plan["output_directory"]
    assert (
        "img-1" not in plan["output_directory"] or "img-1-" in plan["output_directory"]
    )


def test_processed_preview_requires_current_accepted_visibility(tmp_path: Path) -> None:
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    workflow = _workflow(tmp_path, source)
    with pytest.raises(ValueError, match="accepted visibility"):
        workflow.preview_culture_crop_export("img-1", tier="Processed")


def test_accept_publishes_numbered_run_and_records_current_tier(
    tmp_path: Path,
) -> None:
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    workflow = _workflow(tmp_path, source)
    plan = workflow.preview_culture_crop_export(
        "img-1",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    result = workflow.accept_culture_crop_export("img-1", plan)
    assert result["status"] == "ACCEPTED"
    assert workflow.image_record("img-1")["culture"]["status"] == "ACCEPTED"
    assert Path(result["output_directory"]).name == "Run 001"
    assert (
        workflow.state["images"]["img-1"]["crop_exports"]["Unprocessed"]["request_id"]
        == result["request_id"]
    )
    current = workflow.preview_culture_crop_export(
        "img-1",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    assert current["status"] == "UNCHANGED_CURRENT"
    assert (
        workflow.accept_culture_crop_export("img-1", current)["request_id"]
        == result["request_id"]
    )


def test_accept_rejects_cross_image_or_cross_root_plan(tmp_path: Path) -> None:
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    workflow = _workflow(tmp_path, source)
    plan = workflow.preview_culture_crop_export(
        "img-1",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    wrong_image = dict(plan, image_uid="img-2")
    with pytest.raises(ValueError, match="different Image UID"):
        workflow.accept_culture_crop_export("img-1", wrong_image)
    wrong_root = dict(plan, output_directory=str(tmp_path / "outside" / "Run 001"))
    with pytest.raises(ValueError, match="outside this image"):
        workflow.accept_culture_crop_export("img-1", wrong_root)
