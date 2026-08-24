from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools import finalize_grid_handoff, grid_coordinates


def write_complete_row(path: Path) -> None:
    grid_coordinates.prepare_grid_handoff(path)
    row = {field: "" for field in grid_coordinates.HANDOFF_FIELDS}
    row.update(
        {
            "folder": "session",
            "filename": "plate.jpg",
            "experiment": "E1",
            "set": "A",
            "type": "YPDA",
            "run_label": "Single",
            "image_width": "200",
            "image_height": "160",
            "grid_rows": "8",
            "grid_cols": "10",
            "r1c1_x": "10",
            "r1c1_y": "20",
            "r1clast_x": "100",
            "r1clast_y": "22",
            "r5c1_x": "14",
            "r5c1_y": "60",
            "r5clast_x": "104",
            "r5clast_y": "62",
        }
    )
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=grid_coordinates.HANDOFF_FIELDS,
            delimiter="\t",
        )
        writer.writerow(row)


def test_finalizer_persists_complete_single_grid(tmp_path: Path) -> None:
    handoff = tmp_path / "grid.tsv"
    write_complete_row(handoff)
    outputs = finalize_grid_handoff.watch(
        handoff,
        tmp_path / "assets",
        tmp_path / "control",
        timeout_seconds=1,
        poll_seconds=0,
    )
    assert len(outputs) == 1
    assert not handoff.exists()


def test_finalizer_cleans_cancelled_empty_handoff(tmp_path: Path) -> None:
    handoff = grid_coordinates.prepare_grid_handoff(tmp_path / "grid.tsv")
    control = tmp_path / "control"
    control.write_text("cancel\n", encoding="utf-8")
    assert (
        finalize_grid_handoff.watch(
            handoff,
            tmp_path / "assets",
            control,
            timeout_seconds=1,
            poll_seconds=0,
        )
        == []
    )
    assert not handoff.exists()


def test_finalizer_rejects_completion_without_coordinates(tmp_path: Path) -> None:
    handoff = grid_coordinates.prepare_grid_handoff(tmp_path / "grid.tsv")
    control = tmp_path / "control"
    control.write_text("complete\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="without a complete"):
        finalize_grid_handoff.watch(
            handoff,
            tmp_path / "assets",
            control,
            timeout_seconds=1,
            poll_seconds=0,
        )
