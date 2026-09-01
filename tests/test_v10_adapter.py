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
    layout = project["layouts"]["annotationSet 2"]
    assert [
        (band["profile"], band["row_start"], band["row_end"])
        for band in layout["strain_bands"]
    ] == [("Strain 2", 1, 8)]
    assert {
        key: len(labels)
        for key, labels in layout["strain_bands"][0]["label_sets"].items()
    } == {"A": 10, "B": 10}
    assert {item["code"] for item in project["diagnostics"]} == {
        "SET_LABEL_VARIANTS",
        "UNRESOLVED_IMAGE_LABEL_SET",
    }
    assert len(project["arrangements"]) == 49
    assert len(project["annotation_assignments"]) == 7
    assert {
        key: len(value) for key, value in project["annotation_profiles"].items()
    } == {"strain": 32, "vertical": 8, "other": 10}
    arrangements = {
        (row["arrangement"], row["image_number"]): row
        for row in project["arrangements"]
    }
    for image in project["images"]:
        arrangement = arrangements[(image["arrangement"], image["image_number"])]
        for field in ("sample_description", "set", "media", "condition", "rep"):
            assert image[field] == arrangement[field]
    first = project["images"][0]
    assert first["date_display"] == "14.08.26"
    assert first["date"] == "2026-08-14"
    assert first["time"] == "24h"
    assert first["base_filename"]
    assert first["set_filename"]
    image_a = next(
        image
        for image in project["images"]
        if image["annotation_set"] == "annotationSet 2" and image["set"] == "A"
    )
    image_b = next(
        image
        for image in project["images"]
        if image["annotation_set"] == "annotationSet 2" and image["set"] == "B"
    )
    assert derive_plate_layout(project, image_a["image_uid"])["grid_cols"] == 10
    assert (
        derive_plate_layout(project, image_b["image_uid"])["strain_bands"][0][
            "resolved_label_set"
        ]
        == "B"
    )
    image_c = next(image for image in project["images"] if image["set"] == "c")
    with pytest.raises(ValueError, match="none match"):
        derive_plate_layout(project, image_c["image_uid"])


def test_ordered_profiles_are_bands_and_profile_sets_are_image_variants(
    tmp_path: Path,
) -> None:
    frames = synthetic_frames()
    rows: list[dict[str, object]] = []
    strain_rows = [
        ("Top", "A", "top-a1", 1),
        ("Top", "A", "top-a2", 2),
        ("Top", "B", "top-b1", 1),
        ("Top", "B", "top-b2", 2),
        ("Top", "B", "top-b3", 3),
        ("Bottom", "A", "bottom-a1", 1),
        ("Bottom", "B", "bottom-b1", 1),
        ("Bottom", "B", "bottom-b2", 2),
    ]
    for index, (profile, set_name, label, pos) in enumerate(strain_rows):
        row: dict[str, object] = {
            "Profile*": profile,
            "Set*": set_name,
            "labels_strain": label,
            "Pos": pos,
            "Profile*.1": "Rows",
            "labels_vertical": str(index % 4),
            "Pos.1": index + 1,
        }
        if index == 0:
            row.update(
                {
                    "annotationSet": "annotationSet X",
                    "Type": "strain",
                    "Profile": "Top",
                    "Order": 1,
                }
            )
        elif index == 1:
            row.update(
                {
                    "annotationSet": "annotationSet X",
                    "Type": "strain",
                    "Profile": "Bottom",
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
    frames["Annotations"] = pd.DataFrame(rows)
    project = load_v10(str(write_workbook(tmp_path / "variants.xlsx", frames)))
    raw = project["layouts"]["annotationSet X"]
    assert [
        (band["profile"], band["row_start"], band["row_end"])
        for band in raw["strain_bands"]
    ] == [("Top", 1, 4), ("Bottom", 5, 8)]
    assert len(raw["strain_bands"]) == 2
    resolved_a = derive_plate_layout(project, "I1")
    resolved_b = derive_plate_layout(project, "I2")
    assert resolved_a["grid_cols"] == 2
    assert resolved_b["grid_cols"] == 3
    assert [
        band["resolved_label_set"] for band in resolved_a["strain_bands"]
    ] == ["A", "A"]
    assert [
        band["resolved_label_set"] for band in resolved_b["strain_bands"]
    ] == ["B", "B"]


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
    assert "arrangements" in schema["properties"]
    assert "annotation_assignments" in schema["properties"]
    assert "annotation_profiles" in schema["properties"]
    session_properties = schema["properties"]["sessions"]["items"]["properties"]
    image_properties = schema["properties"]["images"]["items"]["properties"]
    assert session_properties["date"]["type"] == "string"
    assert "sample_description" not in session_properties
    assert {
        "id",
        "sample_description",
        "date_display",
        "time",
        "figure_description_label",
        "filename_status",
    }.issubset(image_properties)
