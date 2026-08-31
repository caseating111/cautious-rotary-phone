from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from tools.applet_workflows import ProjectWorkflow
from tools.grid_coordinates import (
    build_grid_coordinate_asset,
    save_grid_coordinate_asset,
)
from tools.project_state import new_project_state


def _model() -> dict:
    return {
        "contract_version": 1,
        "sessions": [{"session_uid": "S1"}],
        "images": [
            {
                "image_uid": "Image 1",
                "session_uid": "S1",
                "annotation_set": "L1",
            }
        ],
        "layouts": {
            "L1": {
                "contract_version": 1,
                "layout_id": "L1",
                "grid_rows": 5,
                "grid_cols": 3,
                "vertical_labels": [
                    {"pos": row, "label": f"R{row}"} for row in range(1, 6)
                ],
                "strain_bands": [
                    {
                        "order": 1,
                        "row_start": 1,
                        "row_end": 5,
                        "local_grid_cols": 3,
                        "labels": [
                            {"pos": column, "label": f"S{column}"}
                            for column in range(1, 4)
                        ],
                    }
                ],
            }
        },
        "diagnostics": [],
    }


def test_create_from_sanitized_v10_persists_openable_state(tmp_path: Path) -> None:
    workbook = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "v10"
        / "v10_sample_synthetic_sanitized.xlsx"
    )
    workflow = ProjectWorkflow.create_from_v10(workbook, tmp_path)
    assert workflow.project_model["images"]
    assert workflow.project_model["layouts"]
    assert (tmp_path / "z. Metadata" / "State" / "workflow_project.json").is_file()
    assert ProjectWorkflow.open(tmp_path).project_model == workflow.project_model
    with pytest.raises(FileExistsError):
        ProjectWorkflow.create_from_v10(workbook, tmp_path)


def test_stateful_orientation_crop_grid_chain_is_non_destructive() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "Raw" / "session" / "source.jpg"
        source.parent.mkdir(parents=True)
        Image.new("L", (220, 180), 80).save(source)
        original = source.read_bytes()
        workflow = ProjectWorkflow(new_project_state(root, _model()))
        workflow.record_setup(
            {
                "preview_only": False,
                "images": [
                    {
                        "image_uid": "Image 1",
                        "raw_path": str(source.relative_to(root)),
                        "working_path": str(source.relative_to(root)),
                        "disposition": "UNCHANGED_CURRENT",
                    }
                ],
            }
        )

        proposed_orientation, preview = workflow.propose_orientation(
            "Image 1", (10, 20, 210, 30)
        )
        assert proposed_orientation["status"] == "PROPOSED"
        assert preview.size == (220, 180)
        accepted_orientation, oriented_path = workflow.accept_orientation(
            "Image 1", proposed_orientation
        )
        assert accepted_orientation["status"] == "ACCEPTED"
        assert oriented_path.is_file()
        assert oriented_path.suffix == ".png"
        with Image.open(oriented_path) as oriented_image:
            assert oriented_image.size == (220, 180)
        retry_orientation, _ = workflow.propose_orientation(
            "Image 1", (10, 20, 210, 30)
        )
        assert Path(retry_orientation["source_path"]) == source

        calibration = workflow.accept_crop_calibration(
            (10, 0), (145, 0), (0, 5), (0, 177), calibration_id="C1"
        )
        assert calibration["side_pixels"] == 100
        proposed_crop, crop_preview = workflow.propose_crop(
            "Image 1", "C1", (20, 0), (0, 30)
        )
        assert proposed_crop["status"] == "PROPOSED"
        assert crop_preview.size == (100, 100)
        accepted_crop, crop_path = workflow.accept_crop("Image 1", proposed_crop)
        assert accepted_crop["status"] == "ACCEPTED"
        assert crop_path.is_file()
        assert crop_path.suffix == ".png"
        with Image.open(crop_path) as cropped_image:
            assert cropped_image.size == (100, 100)
        assert source.read_bytes() == original
        assert workflow.source_for("Image 1") == crop_path

        asset = build_grid_coordinate_asset(
            image_ref=str(crop_path),
            image_width=100,
            image_height=100,
            grid_rows=5,
            grid_cols=3,
            image_uid="Image 1",
            reference_points={
                "r1c1": {"x": 10, "y": 10},
                "r1clast": {"x": 90, "y": 10},
                "r5c1": {"x": 10, "y": 90},
                "r5clast": {"x": 90, "y": 90},
            },
        )
        asset_path = save_grid_coordinate_asset(asset, root / "GridCoordinates")
        workflow.attach_grid_asset("Image 1", asset_path)
        assert workflow.grid_asset("Image 1")["spots"]["r1c1"] == {
            "row": 1,
            "column": 1,
            "x": 10.0,
            "y": 10.0,
        }

        visibility_proposal, visibility_preview = workflow.propose_visibility("Image 1")
        assert visibility_proposal["status"] == "PROPOSED"
        assert visibility_preview.size == (100, 100)
        visibility, visibility_path, visibility_sidecar = workflow.accept_visibility(
            "Image 1", visibility_proposal
        )
        assert visibility["status"] == "ACCEPTED"
        assert visibility_path.is_file() and visibility_sidecar.is_file()
        assert visibility_path.suffix == ".png"

        annotation_proposal, annotation_preview = workflow.propose_annotation("Image 1")
        assert annotation_proposal["status"] == "PROPOSED"
        assert annotation_preview.width > 100
        annotation, annotation_path, annotation_sidecar = workflow.accept_annotation(
            "Image 1", annotation_proposal
        )
        assert annotation["status"] == "ACCEPTED"
        assert annotation_path.is_file() and annotation_sidecar.is_file()

        reopened = ProjectWorkflow.open(root)
        record = reopened.image_record("Image 1")
        assert record["orientation"]["status"] == "ACCEPTED"
        assert record["crop"]["status"] == "ACCEPTED"
        assert record["grid"]["status"] == "ACCEPTED"
        assert record["visibility"]["status"] == "ACCEPTED"
        assert record["annotation"]["status"] == "ACCEPTED"


def test_orientation_retry_and_skip_use_pre_orientation_source(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("L", (220, 180), 80).save(source)
    workflow = ProjectWorkflow(new_project_state(tmp_path, _model()))
    workflow.record_setup(
        {
            "images": [
                {
                    "image_uid": "Image 1",
                    "raw_path": str(source),
                    "working_path": str(source),
                    "disposition": "READY",
                }
            ]
        }
    )
    proposed, _ = workflow.propose_orientation("Image 1", (10, 20, 210, 30))
    _accepted, first_output = workflow.accept_orientation("Image 1", proposed)
    assert first_output.suffix == ".png"
    retry, _ = workflow.propose_orientation("Image 1", (10, 20, 210, 30))
    assert Path(retry["source_path"]) == source
    skipped_proposal, _ = workflow.propose_orientation("Image 1", None, skip=True)
    skipped, skipped_output = workflow.accept_orientation(
        "Image 1", skipped_proposal
    )
    assert skipped["status"] == "SKIPPED"
    assert skipped_output != first_output
    assert skipped_output.read_bytes() == source.read_bytes()


def test_optional_derivative_skips_are_recorded_and_resumable(tmp_path: Path) -> None:
    workflow = ProjectWorkflow(new_project_state(tmp_path, _model()))
    visibility = workflow.skip_derivative("Image 1", "visibility")
    annotation = workflow.skip_derivative("Image 1", "annotation")
    assert visibility["status"] == "SKIPPED"
    assert annotation["status"] == "SKIPPED"
    reopened = ProjectWorkflow.open(tmp_path)
    assert reopened.image_record("Image 1")["visibility"]["status"] == "SKIPPED"
    assert reopened.image_record("Image 1")["annotation"]["status"] == "SKIPPED"


def test_proposals_cannot_cross_image_or_unknown_calibration_boundaries(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    Image.new("L", (100, 100), 0).save(source)
    workflow = ProjectWorkflow(new_project_state(tmp_path, _model()))
    workflow.record_setup(
        {
            "images": [
                {
                    "image_uid": "Image 1",
                    "raw_path": str(source),
                    "working_path": str(source),
                    "disposition": "READY",
                }
            ]
        }
    )
    proposed, _ = workflow.propose_orientation("Image 1", (0, 0, 90, 3))
    proposed["image_uid"] = "other"
    with pytest.raises(ValueError, match="different Image UID"):
        workflow.accept_orientation("Image 1", proposed)
    with pytest.raises(ValueError, match="Unknown crop calibration"):
        workflow.propose_crop("Image 1", "missing", (0, 0), (0, 0))


def test_source_selection_and_grid_auto_discovery_are_explicit(tmp_path: Path) -> None:
    workflow = ProjectWorkflow(new_project_state(tmp_path, _model()))
    working = tmp_path / "1. b. Working" / "plate.png"
    cropped = tmp_path / "2. Cropped" / "plate.png"
    processed = tmp_path / "3. Processed" / "plate.png"
    for path, shade in ((working, 10), (cropped, 20), (processed, 30)):
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (100, 100), shade).save(path)
    record = workflow.image_record("Image 1")
    record["working_path"] = str(working.relative_to(tmp_path))
    record["crop"] = {"status": "ACCEPTED", "output_path": str(cropped)}
    record["visibility"] = {"status": "ACCEPTED", "output_path": str(processed)}
    workflow.save()

    assert workflow.source_for("Image 1") == cropped
    assert workflow.source_for("Image 1", source_kind="processed") == processed
    assert workflow.source_for("Image 1", source_kind="working") == working

    asset = build_grid_coordinate_asset(
        image_ref=str(cropped),
        image_width=100,
        image_height=100,
        grid_rows=5,
        grid_cols=3,
        image_uid="Image 1",
        reference_points={
            "r1c1": {"x": 10, "y": 10},
            "r1clast": {"x": 90, "y": 10},
            "r5c1": {"x": 10, "y": 90},
            "r5clast": {"x": 90, "y": 90},
        },
    )
    canonical = tmp_path / "z. Metadata" / "State" / "GridCoordinates"
    asset_path = save_grid_coordinate_asset(asset, canonical)
    found = workflow.auto_attach_grids()
    assert found["attached"]["Image 1"] == str(asset_path)
    assert not found["ambiguous"]

    legacy = tmp_path / "GridCoordinates"
    legacy.mkdir()
    shutil.copy2(asset_path, legacy / asset_path.name)
    ambiguous = workflow.auto_attach_grids()
    assert "Image 1" in ambiguous["ambiguous"]
