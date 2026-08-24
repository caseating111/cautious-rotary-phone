from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from tools.applets.mixed_tier_matrix import (
    enumerate_crop_candidates,
    plan_mixed_tier_matrix,
    preview_mixed_tier_matrix,
    publish_mixed_tier_matrix,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state(tmp_path: Path) -> dict:
    model_images = []
    images = {}
    specifications = (
        ("I1", "Unprocessed", "Top", "WT", 40),
        ("I2", "Processed", "Low", "MUT", 160),
    )
    for index, (uid, source_tier, state_name, strain, value) in enumerate(
        specifications, start=1
    ):
        output = tmp_path / "Crops" / source_tier / uid / "Run 001"
        output.mkdir(parents=True)
        crop = output / f"{uid}_{state_name}.png"
        Image.new("L", (20, 30), value).save(crop)
        export = {
            "status": "ACCEPTED",
            "request_id": f"{index:064x}",
            "output_directory": str(output),
            "grid_asset_id": f"grid-{uid}",
            "layout_id": "L1",
            "crops": [
                {
                    "crop_id": f"{state_name.lower()}-c1",
                    "state": state_name,
                    "column": 1,
                    "strain_label": strain,
                    "filename": crop.name,
                    "sha256": _digest(crop),
                }
            ],
        }
        images[uid] = {
            "image_uid": uid,
            "crop_exports": {source_tier: export},
        }
        model_images.append(
            {
                "image_uid": uid,
                "session_uid": f"S{index}",
                "exp": "E1",
                "set": str(index),
                "condition": "YPDA",
            }
        )
    return {
        "project_root": str(tmp_path),
        "project_model": {
            "images": model_images,
            "sessions": [
                {"session_uid": "S1", "date": "2026-08-24"},
                {"session_uid": "S2", "date": "2026-08-25"},
            ],
        },
        "images": images,
    }


def _mixed_plan(tmp_path: Path) -> tuple[dict, dict[str, dict]]:
    state = _state(tmp_path)
    candidates = enumerate_crop_candidates(state)
    by_state = {value["state"]: key for key, value in candidates.items()}
    plan = plan_mixed_tier_matrix(
        state,
        [
            {"candidate_id": by_state["Top"], "row": "WT", "column": "Plate"},
            {"candidate_id": by_state["Low"], "row": "MUT", "column": "Plate"},
        ],
        rows=["WT", "MUT"],
        columns=["Plate"],
    )
    return plan, candidates


def test_candidates_keep_source_tier_state_and_canonical_provenance(
    tmp_path: Path,
) -> None:
    candidates = enumerate_crop_candidates(_state(tmp_path))
    assert {item["source_tier"] for item in candidates.values()} == {
        "Unprocessed",
        "Processed",
    }
    assert {item["state"] for item in candidates.values()} == {"Top", "Low"}
    assert {item["export_request_id"] for item in candidates.values()} == {
        f"{1:064x}",
        f"{2:064x}",
    }
    assert all(
        item["default_column"].endswith(item["image_uid"])
        for item in candidates.values()
    )


def test_stale_candidates_are_unavailable_and_hash_mismatch_fails(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state["images"]["I2"]["crop_exports"]["Processed"]["status"] = "STALE"
    candidates = enumerate_crop_candidates(state)
    assert {item["image_uid"] for item in candidates.values()} == {"I1"}
    crop = next(Path(item["path"]) for item in candidates.values())
    crop.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        enumerate_crop_candidates(state)


def test_plan_requires_one_unique_selection_for_every_cell(tmp_path: Path) -> None:
    state = _state(tmp_path)
    candidates = enumerate_crop_candidates(state)
    ids = list(candidates)
    with pytest.raises(ValueError, match="Every matrix"):
        plan_mixed_tier_matrix(
            state,
            [{"candidate_id": ids[0], "row": "WT", "column": "P"}],
            rows=["WT", "MUT"],
            columns=["P"],
        )
    with pytest.raises(ValueError, match="unique ignoring case"):
        plan_mixed_tier_matrix(
            state,
            [],
            rows=["WT", "wt"],
            columns=["P"],
        )
    with pytest.raises(ValueError, match="unique row/column"):
        plan_mixed_tier_matrix(
            state,
            [
                {"candidate_id": ids[0], "row": "WT", "column": "P"},
                {"candidate_id": ids[1], "row": "WT", "column": "P"},
            ],
            rows=["WT"],
            columns=["P", "Q"],
        )


def test_preview_is_zero_write_and_preserves_mixed_top_low_selection(
    tmp_path: Path,
) -> None:
    plan, candidates = _mixed_plan(tmp_path)
    originals = {
        key: (Path(item["path"]).read_bytes(), Image.open(item["path"]).size)
        for key, item in candidates.items()
    }
    preview = preview_mixed_tier_matrix(plan)
    assert preview["status"] == "PREVIEW"
    assert preview["tile_count"] == 2
    assert preview["preview_image"].size == tuple(preview["output_dimensions"])
    assert {item["tier"] for item in plan["items"]} == {"Top", "Low"}
    assert {item["source_tier"] for item in plan["items"]} == {
        "Unprocessed",
        "Processed",
    }
    assert not Path(plan["output_root"]).exists()
    for key, item in candidates.items():
        path = Path(item["path"])
        with Image.open(path) as image:
            assert (path.read_bytes(), image.size) == originals[key]


def test_publish_is_atomic_numbered_and_idempotent(tmp_path: Path) -> None:
    plan, candidates = _mixed_plan(tmp_path)
    source_hashes = {
        key: _digest(Path(item["path"])) for key, item in candidates.items()
    }
    result = publish_mixed_tier_matrix(plan)
    output = Path(result["output_directory"])
    assert output.name == "Run 001"
    assert Path(result["output_path"]).is_file()
    assert (output / "matrix_export.json").is_file()
    assert result["matrix_sha256"] == _digest(Path(result["output_path"]))
    assert not list(Path(plan["output_root"]).glob(".mixed-matrix-*"))
    again = publish_mixed_tier_matrix(plan)
    assert again["request_id"] == result["request_id"]
    assert again["output_directory"] == result["output_directory"]
    assert {
        key: _digest(Path(item["path"])) for key, item in candidates.items()
    } == source_hashes


def test_changed_input_after_preview_fails_before_publish(tmp_path: Path) -> None:
    plan, _candidates = _mixed_plan(tmp_path)
    Path(plan["items"][0]["image"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed after preview"):
        publish_mixed_tier_matrix(plan)
    assert not Path(plan["output_root"]).exists()
