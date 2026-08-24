from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.applets.annotation import derive_annotation_positions
from tools.applets.visibility import calculate_grid_roi
from tools.grid_coordinates import (
    build_grid_coordinate_asset,
    persist_grid_handoff,
    prepare_grid_handoff,
    save_grid_coordinate_asset,
    spot_list,
    spot_mapping,
    validate_grid_coordinate_asset,
)


def references() -> dict[str, dict[str, float]]:
    return {
        "r1c1": {"x": 10.0, "y": 20.0},
        "r1clast": {"x": 100.0, "y": 22.0},
        "r5c1": {"x": 14.0, "y": 60.0},
        "r5clast": {"x": 104.0, "y": 62.0},
    }


def asset() -> dict:
    return build_grid_coordinate_asset(
        image_ref="session/image1.jpg",
        image_width=200,
        image_height=160,
        grid_rows=8,
        grid_cols=10,
        reference_points=references(),
        experiment="E1",
        set_name="A",
        type_name="YPDA",
        run_label="Single",
        accepted_at="2026-08-24T12:00:00+00:00",
    )


def test_builds_rows_columns_and_named_spots_in_explicit_space() -> None:
    value = asset()
    validate_grid_coordinate_asset(value)
    assert value["coordinate_space"] == {
        "id": "source_image_pixels",
        "origin": "top_left",
        "x_axis": "right",
        "y_axis": "down",
        "units": "pixels",
        "position_semantics": "continuous_pixel_centres",
        "image_width": 200,
        "image_height": 160,
    }
    assert len(value["spots"]) == 80
    assert value["spots"]["r1c1"] == {"row": 1, "column": 1, "x": 10.0, "y": 20.0}
    assert value["spots"]["r5c1"] == {"row": 5, "column": 1, "x": 14.0, "y": 60.0}
    assert value["spots"]["r8c10"]["x"] == pytest.approx(107.0)
    assert value["spots"]["r8c10"]["y"] == pytest.approx(92.0)
    assert value["provenance"]["accepted_after"] == "accepted_alignment_and_crop_export"
    assert len(value["row_coordinates"]) == 8
    assert len(value["column_coordinates"]) == 10


def test_spot_adapters_are_deterministic() -> None:
    value = asset()
    mapping = spot_mapping(value)
    ordered = spot_list(value)
    assert mapping[(1, 1)] == (10.0, 20.0)
    assert mapping[(5, 10)] == (104.0, 62.0)
    assert ordered[0] == mapping[(1, 1)]
    assert ordered[-1] == mapping[(8, 10)]


def test_image_identity_uses_windows_case_and_separator_semantics() -> None:
    canonical = asset()
    variant = build_grid_coordinate_asset(
        image_ref=r"SESSION\IMAGE1.JPG",
        image_width=200,
        image_height=160,
        grid_rows=8,
        grid_cols=10,
        reference_points=references(),
    )
    assert variant["image_ref"] == "SESSION/IMAGE1.JPG"
    assert variant["asset_id"] == canonical["asset_id"]

def test_invalid_or_incomplete_spot_state_fails_closed() -> None:
    value = asset()
    del value["spots"]["r1c1"]
    with pytest.raises(ValueError, match="cover every"):
        validate_grid_coordinate_asset(value)


def test_asset_and_index_are_written_atomically_and_replaced_by_identity(
    tmp_path: Path,
) -> None:
    first = save_grid_coordinate_asset(asset(), tmp_path)
    second_value = asset()
    second_value["provenance"]["accepted_at"] = "2026-08-24T13:00:00+00:00"
    second = save_grid_coordinate_asset(second_value, tmp_path)
    assert first == second
    saved = json.loads(first.read_text(encoding="utf-8"))
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert saved["provenance"]["accepted_at"] == "2026-08-24T13:00:00+00:00"
    assert index["assets"]["session/image1.jpg"]["path"] == first.name
    assert not list(tmp_path.glob("*.tmp"))


def test_fiji_handoff_is_converted_and_removed(tmp_path: Path) -> None:
    handoff = tmp_path / "grid.tsv"
    fields = [
        "folder",
        "filename",
        "experiment",
        "set",
        "type",
        "image_uid",
        "run_label",
        "image_width",
        "image_height",
        "grid_rows",
        "grid_cols",
        "r1c1_x",
        "r1c1_y",
        "r1clast_x",
        "r1clast_y",
        "r5c1_x",
        "r5c1_y",
        "r5clast_x",
        "r5clast_y",
    ]
    prepare_grid_handoff(handoff)
    row = {
        "folder": "session",
        "filename": "image1.jpg",
        "experiment": "E1",
        "set": "A",
        "type": "YPDA",
        "image_uid": "",
        "run_label": "Batch All",
        "image_width": 200,
        "image_height": 160,
        "grid_rows": 8,
        "grid_cols": 10,
        "r1c1_x": 10,
        "r1c1_y": 20,
        "r1clast_x": 100,
        "r1clast_y": 22,
        "r5c1_x": 14,
        "r5c1_y": 60,
        "r5clast_x": 104,
        "r5clast_y": 62,
    }
    with handoff.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writerow(row)
    outputs = persist_grid_handoff(handoff, tmp_path / "assets")
    assert len(outputs) == 1
    assert not handoff.exists()
    saved = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert saved["image_ref"] == "session/image1.jpg"
    assert saved["provenance"]["run_label"] == "Batch All"


def test_production_consumers_accept_grid_coordinate_asset() -> None:
    value = asset()
    roi = calculate_grid_roi(value, padding=0)
    assert roi["right"] == pytest.approx(107.0)
    assert roi["bottom"] == pytest.approx(92.0)
    layout = {
        "grid_rows": 8,
        "grid_cols": 10,
        "vertical_labels": [{"pos": 1, "label": "YPDA"}],
        "strain_bands": [
            {
                "order": 1,
                "row_start": 1,
                "row_end": 8,
                "labels": [{"pos": 1, "label": "WT"}],
            }
        ],
    }
    positions = derive_annotation_positions(layout, value)
    assert positions["vertical_placements"][0]["label"] == "YPDA"
    assert positions["strain_placements"][0]["label"] == "WT"
    assert positions["col_x"][1] == pytest.approx(13.5)
