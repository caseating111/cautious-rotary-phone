from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from tools.applet_workflows import ProjectWorkflow
from tools.project_state import new_project_state, record_crop_export


def _workflow(tmp_path: Path) -> ProjectWorkflow:
    model = {
        "contract_version": 1,
        "sessions": [
            {"session_uid": "S1", "date": "2026-08-24"},
            {"session_uid": "S2", "date": "2026-08-25"},
        ],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "S1",
                "exp": "E1",
                "set": "A",
                "condition": "YPDA",
            },
            {
                "image_uid": "I2",
                "session_uid": "S2",
                "exp": "E1",
                "set": "B",
                "condition": "YPDA",
            },
        ],
    }
    state = new_project_state(tmp_path, model)
    for uid, source_tier, culture_state, strain, value in (
        ("I1", "Unprocessed", "Top", "WT", 40),
        ("I2", "Processed", "Low", "MUT", 160),
    ):
        output = tmp_path / "Crops" / source_tier / uid / "Run 001"
        output.mkdir(parents=True)
        crop = output / f"{uid}_{culture_state}.png"
        Image.new("L", (20, 30), value).save(crop)
        digest = hashlib.sha256(crop.read_bytes()).hexdigest()
        record_crop_export(
            state,
            uid,
            source_tier,
            {
                "status": "ACCEPTED",
                "request_id": hashlib.sha256(uid.encode()).hexdigest(),
                "output_directory": str(output),
                "crops": [
                    {
                        "crop_id": f"{culture_state.lower()}-c1",
                        "state": culture_state,
                        "column": 1,
                        "strain_label": strain,
                        "filename": crop.name,
                        "sha256": digest,
                    }
                ],
            },
        )
    return ProjectWorkflow(state)


def _selection(workflow: ProjectWorkflow) -> tuple[list[dict[str, str]], list[str]]:
    candidates = workflow.mixed_tier_crop_candidates()
    by_state = {candidate["state"]: candidate for candidate in candidates.values()}
    selections = [
        {
            "candidate_id": by_state["Top"]["candidate_id"],
            "row": "WT",
            "column": "Plate",
        },
        {
            "candidate_id": by_state["Low"]["candidate_id"],
            "row": "MUT",
            "column": "Plate",
        },
    ]
    return selections, list(candidates)


def test_workflow_previews_accepts_and_persists_mixed_tier_matrix(
    tmp_path: Path,
) -> None:
    workflow = _workflow(tmp_path)
    selections, _ids = _selection(workflow)
    plan, preview = workflow.propose_mixed_tier_matrix(
        selections,
        rows=["WT", "MUT"],
        columns=["Plate"],
    )
    assert preview.size == (
        plan["matrix_layout"]["tile_size"][0] + 120,
        2 * (plan["matrix_layout"]["tile_size"][1] + 10) + 50,
    )
    result = workflow.accept_mixed_tier_matrix(plan)
    assert Path(result["output_path"]).is_file()
    assert result["request_id"] in workflow.state["matrix_exports"]
    reopened = ProjectWorkflow.open(tmp_path)
    assert result["request_id"] in reopened.state["matrix_exports"]


def test_workflow_rejects_stale_candidate_and_cross_project_root(
    tmp_path: Path,
) -> None:
    workflow = _workflow(tmp_path)
    selections, _ids = _selection(workflow)
    plan, _preview = workflow.propose_mixed_tier_matrix(
        selections,
        rows=["WT", "MUT"],
        columns=["Plate"],
    )
    wrong_root = dict(plan, output_root=str(tmp_path / "outside"))
    with pytest.raises(ValueError, match="outside this project"):
        workflow.accept_mixed_tier_matrix(wrong_root)
    workflow.state["images"]["I2"]["crop_exports"]["Processed"]["status"] = "STALE"
    with pytest.raises(ValueError, match="no longer current"):
        workflow.accept_mixed_tier_matrix(plan)
