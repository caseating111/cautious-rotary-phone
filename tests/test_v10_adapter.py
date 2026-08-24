from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tools.applets.v10_adapter import (
    derive_plate_layout,
    load_v10,
    project_to_legacy_images_rows,
    reconcile_image_files,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SANITIZED = REPO_ROOT / "fixtures" / "v10" / "v10_sample_synthetic_sanitized.xlsx"


def synthetic_frames() -> dict[str, pd.DataFrame]:
    overview = pd.DataFrame(
        [
            {
                "Include": True,
                "sessionUID*": "S1",
                "Exp*": 2,
                "Date*": "2026-08-16",
                "Time": "24h",
                "Arrangement*": "Arrangement X",
                "annotationSet*": "annotationSet X",
            }
        ]
    )
    master = pd.DataFrame(
        [
            {
                "sessionUID*": "S1",
                "Image #": 1,
                "Image UID": "I1",
                "Original": "image1.jpg",
                "Working filename": "working 1.jpg",
                "Exp": 2,
                "Set": None,
                "Set*": "A",
                "Media": "YPDA",
                "Condition": None,
                "Rep #": 1,
                "Arrangement": "Arrangement X",
                "annotationSet": "annotationSet X",
            },
            {
                "sessionUID*": "S1",
                "Image #": 2,
                "Image UID": "I2",
                "Original": "image2.jpg",
                "Working filename": "working 2.jpg",
                "Exp": 2,
                "Set": "human-old",
                "Set*": "B",
                "Media": None,
                "Condition": "heat",
                "Rep #": 2,
                "Arrangement": "Arrangement X",
                "annotationSet": "annotationSet X",
            },
        ]
    )
    rows: list[dict[str, object]] = []
    for index in range(8):
        row: dict[str, object] = {
            "Profile*.1": "Rows",
            "labels_vertical": str(index % 4),
            "Pos.1": index + 1,
        }
        if index < 4:
            row.update(
                {
                    "Profile*": "Upper",
                    "Set*": "A",
                    "labels_strain": f"u{index + 1}",
                    "Pos": index + 1,
                }
            )
        elif index < 6:
            row.update(
                {
                    "Profile*": "Lower",
                    "Set*": "B",
                    "labels_strain": f"l{index - 3}",
                    "Pos": index - 3,
                }
            )
        if index == 0:
            row.update(
                {
                    "annotationSet": "annotationSet X",
                    "Type": "strain",
                    "Profile": "Upper",
                    "Order": 1,
                }
            )
        elif index == 1:
            row.update(
                {
                    "annotationSet": "annotationSet X",
                    "Type": "strain",
                    "Profile": "Lower",
                    "Order": 2,
                }
            )
        elif index == 2:
            row.update(
                {
                    "annotationSet": "annotationSet X",
                    "Type": "vertical",
                    "Profile": "Rows",
                    "Order": 1,
                }
            )
        rows.append(row)
    annotations = pd.DataFrame(rows)
    return {
        "Overview": overview,
        "Arrangements": pd.DataFrame([{"Arrangement": "Arrangement X"}]),
        "Annotations": annotations,
        "Master Registry": master,
    }


def write_workbook(path: Path, frames: dict[str, pd.DataFrame]) -> Path:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, frame in frames.items():
            frame.to_excel(writer, sheet_name=sheet, index=False, startrow=1)
    return path


def test_sanitized_fixture_is_normalized_and_embeds_layouts() -> None:
    project = load_v10(str(SANITIZED))
    assert len(project["sessions"]) == 4
    assert len(project["images"]) == 98
    assert set(project["layouts"]) == {"annotationSet 1", "annotationSet 2"}
    assert (
        project["layouts"]["annotationSet 1"]["grid_rows"],
        project["layouts"]["annotationSet 1"]["grid_cols"],
    ) == (8, 12)
    assert (
        project["layouts"]["annotationSet 2"]["grid_rows"],
        project["layouts"]["annotationSet 2"]["grid_cols"],
    ) == (8, 10)
    assert len(project["diagnostics"]) == 1
    assert project["diagnostics"][0]["code"] == "LEGACY_SET_BLOCK_BANDS"


def test_ordered_profiles_machine_set_types_and_embedded_derivation(
    tmp_path: Path,
) -> None:
    path = write_workbook(tmp_path / "ordered.xlsx", synthetic_frames())
    project = load_v10(str(path))
    assert [image["set"] for image in project["images"]] == ["A", "B"]
    layout = project["layouts"]["annotationSet X"]
    assert (layout["grid_rows"], layout["grid_cols"]) == (8, 4)
    assert [
        (band["order"], band["row_start"], band["row_end"], band["local_grid_cols"])
        for band in layout["strain_bands"]
    ] == [
        (1, 1, 4, 4),
        (2, 5, 8, 2),
    ]
    assert {band["row_mapping_provenance"] for band in layout["strain_bands"]} == {
        "even_split"
    }
    assert derive_plate_layout(project, "I2")["layout_id"] == "annotationSet X"


def test_duplicate_and_missing_image_fields_fail_closed(tmp_path: Path) -> None:
    frames = synthetic_frames()
    frames["Master Registry"].loc[1, "Image UID"] = "I1"
    with pytest.raises(ValueError, match="Duplicate Image UID"):
        load_v10(str(write_workbook(tmp_path / "duplicate.xlsx", frames)))

    frames = synthetic_frames()
    frames["Master Registry"].loc[1, ["Set", "Set*"]] = None
    with pytest.raises(ValueError, match="missing Set"):
        load_v10(str(write_workbook(tmp_path / "missing.xlsx", frames)))


def test_duplicate_positions_and_ambiguous_orders_fail_closed(tmp_path: Path) -> None:
    frames = synthetic_frames()
    frames["Annotations"].loc[5, "Pos"] = 1
    with pytest.raises(ValueError, match="duplicate Pos"):
        load_v10(str(write_workbook(tmp_path / "duplicate-pos.xlsx", frames)))

    frames = synthetic_frames()
    frames["Annotations"].loc[1, "Order"] = 1
    with pytest.raises(ValueError, match="Order values must be unique"):
        load_v10(str(write_workbook(tmp_path / "duplicate-order.xlsx", frames)))


def test_multiple_vertical_assignments_fail_closed(tmp_path: Path) -> None:
    frames = synthetic_frames()
    frames["Annotations"].loc[3, ["annotationSet", "Type", "Profile", "Order"]] = [
        "annotationSet X",
        "vertical",
        "Rows",
        2,
    ]
    with pytest.raises(ValueError, match="exactly one vertical profile"):
        load_v10(str(write_workbook(tmp_path / "vertical.xlsx", frames)))


def test_reconciliation_missing_values_and_basic_csv_terminology(
    tmp_path: Path,
) -> None:
    project = load_v10(str(write_workbook(tmp_path / "valid.xlsx", synthetic_frames())))
    result = reconcile_image_files(
        project, {"S1": ["image1.jpg", "PROCESSED working 2.tif", "extra.jpg"]}
    )
    assert [item["status"] for item in result["images"]] == ["READY", "READY"]
    assert result["summary"]["unmapped_count"] == 1
    rows = project_to_legacy_images_rows(project)
    assert {"Filename", "Experiment", "Set", "Type"}.issubset(rows[0])
    assert rows[0]["Experiment"] == "2"
    assert rows[1]["Type"] == "heat"


def test_project_schema_declares_embedded_layouts_and_diagnostics() -> None:
    schema = json.loads(
        (REPO_ROOT / "contracts" / "project_model.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert "layouts" in schema["properties"]
    assert "diagnostics" in schema["properties"]
