from __future__ import annotations

from pathlib import Path

import pytest

from tools.project_dates import (
    find_date_tokens,
    replace_date_token,
    unique_folder_date,
    working_filename_for,
)
from tools.project_lifecycle import (
    apply_layout_migration,
    apply_loose_image_import,
    discover_experiment_folders,
    mark_working_complete,
    match_experiment_folder,
    plan_layout_migration,
    plan_loose_image_import,
)
from tools.applet_workflows import ProjectWorkflow
from tools.project_state import (
    load_project_state,
    new_project_state,
    save_project_state,
)


def model() -> dict:
    return {
        "contract_version": 1,
        "sessions": [
            {"session_uid": "E2_14.08.26_24H", "exp": "2", "date": "2026-08-14"},
            {"session_uid": "E3_14.08.26_24H", "exp": "3", "date": "2026-08-14"},
        ],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "E2_14.08.26_24H",
                "image_number": 1,
                "original": "image1.jpg",
                "working_filename": "14.08.26_SetA_plate.jpg",
                "exp": "2",
                "set": "A",
                "annotation_set": "L1",
            },
            {
                "image_uid": "I2",
                "session_uid": "E3_14.08.26_24H",
                "image_number": 1,
                "original": "other.jpg",
                "working_filename": "14.08.26_SetA_other.jpg",
                "exp": "3",
                "set": "A",
                "annotation_set": "L1",
            },
        ],
    }


@pytest.mark.parametrize(
    "name",
    [
        "14.08.26 EXP2",
        "14-08-26 EXP2",
        "14_08_26 EXP2",
        "2026.08.14 EXP2",
        "2026-08-14 EXP2",
        "2026_08_14 EXP2",
    ],
)
def test_folder_date_forms_and_session_matching(name: str, tmp_path: Path) -> None:
    folder = tmp_path / name
    folder.mkdir()
    (folder / "image1.jpg").write_bytes(b"synthetic")
    assert unique_folder_date(name).isoformat() == "2026-08-14"
    match = match_experiment_folder(folder, model())
    assert match.status == "MATCHED"
    assert match.session_uid == "E2_14.08.26_24H"


def test_date_conversion_is_idempotent_and_uses_v10_date() -> None:
    session = {"date": "2026-08-14"}
    image = {"working_filename": "14.08.26_SetA.jpg"}
    assert working_filename_for(image, session, date_style="yyyy.mm.dd") == "2026.08.14_SetA.jpg"
    assert replace_date_token("2026.08.14_SetA.jpg", unique_folder_date("2026.08.14"), "yyyy.mm.dd") == "2026.08.14_SetA.jpg"
    assert len(find_date_tokens("2026.08.14_SetA.jpg")) == 1


def test_loose_import_and_working_completion_are_resumable(tmp_path: Path) -> None:
    source = tmp_path / "image1.jpg"
    source.write_bytes(b"source")
    preview = plan_loose_image_import(tmp_path)
    assert preview["items"][0]["status"] == "WOULD_MOVE"
    applied = apply_loose_image_import(preview)
    assert applied["items"][0]["status"] == "MOVED_TO_RAW"
    assert (tmp_path / "1. a. Raw" / "image1.jpg").read_bytes() == b"source"

    state = new_project_state(tmp_path, {**model(), "sessions": model()["sessions"][:1], "images": model()["images"][:1]})
    working = tmp_path / "1. b. Working"
    working.mkdir()
    (working / "renamed.jpg").write_bytes(b"working")
    state["images"]["I1"]["working_path"] = "1. b. Working/renamed.jpg"
    result = mark_working_complete(state)
    assert result["status"] == "COMPLETE"
    assert (tmp_path / "2. Cropped" / "1. b. Working" / "renamed.jpg").is_file()
    assert state["images"]["I1"]["working_path"] == "2. Cropped/1. b. Working/renamed.jpg"
    assert mark_working_complete(state)["status"] == "UNCHANGED_CURRENT"


def test_state_rebases_after_external_project_folder_rename(tmp_path: Path) -> None:
    root = tmp_path / "14.08.26 EXP2"
    state = new_project_state(root, {**model(), "sessions": model()["sessions"][:1], "images": model()["images"][:1]})
    state["images"]["I1"]["working_path"] = str(root / "1. b. Working" / "x.jpg")
    save_project_state(state)
    moved = tmp_path / "2026.08.14 EXP2"
    root.rename(moved)
    loaded = load_project_state(moved)
    assert Path(loaded["project_root"]) == moved.resolve()
    assert str(moved) in loaded["images"]["I1"]["working_path"]


def test_program_folder_date_rename_keeps_one_openable_state(tmp_path: Path) -> None:
    root = tmp_path / "14-08-26 EXP2"
    workflow = ProjectWorkflow(
        new_project_state(
            root,
            {**model(), "sessions": model()["sessions"][:1], "images": model()["images"][:1]},
        )
    )
    workflow.save()
    moved = workflow.rename_project_date()
    assert moved.name == "2026.08.14 EXP2"
    reopened = ProjectWorkflow.open(moved)
    assert reopened.project_root == moved.resolve()
    assert list(moved.rglob("workflow_project.json")) == [
        moved / "z. Metadata" / "State" / "workflow_project.json"
    ]


def test_legacy_layout_migration_is_previewed_and_idempotent(tmp_path: Path) -> None:
    (tmp_path / "Raw").mkdir()
    (tmp_path / "Raw" / "image1.jpg").write_bytes(b"raw")
    (tmp_path / "Working").mkdir()
    (tmp_path / "Working" / "working.jpg").write_bytes(b"working")
    state = new_project_state(tmp_path, {**model(), "sessions": model()["sessions"][:1], "images": model()["images"][:1]})
    state["images"]["I1"]["raw_path"] = "Raw/image1.jpg"
    state["images"]["I1"]["working_path"] = "Working/working.jpg"
    plan = plan_layout_migration(tmp_path)
    assert plan["moves"] and not plan["blockers"]
    assert (tmp_path / "Raw").is_dir()
    apply_layout_migration(plan, state)
    assert (tmp_path / "1. a. Raw" / "image1.jpg").is_file()
    assert (tmp_path / "1. b. Working" / "working.jpg").is_file()
    assert state["images"]["I1"]["raw_path"] == "1. a. Raw/image1.jpg"
    assert not plan_layout_migration(tmp_path)["moves"]


def test_legacy_completed_working_and_grids_migrate_to_canonical_state(
    tmp_path: Path,
) -> None:
    completed = tmp_path / "Processed" / "Cropped" / "Working"
    completed.mkdir(parents=True)
    (completed / "working.jpg").write_bytes(b"working")
    grids = tmp_path / "State" / "GridCoordinates"
    grids.mkdir(parents=True)
    (grids / "keep.txt").write_text("grid metadata", encoding="utf-8")
    state = new_project_state(
        tmp_path,
        {**model(), "sessions": model()["sessions"][:1], "images": model()["images"][:1]},
    )
    plan = plan_layout_migration(tmp_path)
    assert not plan["blockers"]
    apply_layout_migration(plan, state)
    assert (tmp_path / "2. Cropped" / "1. b. Working" / "working.jpg").is_file()
    assert (
        tmp_path / "z. Metadata" / "State" / "GridCoordinates" / "keep.txt"
    ).is_file()


def test_parent_discovery_requires_loose_images_or_actual_state_file(
    tmp_path: Path,
) -> None:
    empty_state = tmp_path / "not-a-project" / "State"
    empty_state.mkdir(parents=True)
    real = tmp_path / "14.08.26 EXP2"
    real.mkdir()
    (real / "image1.jpg").write_bytes(b"synthetic")
    assert discover_experiment_folders(tmp_path) == [real.resolve()]
