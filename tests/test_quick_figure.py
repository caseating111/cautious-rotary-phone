from pathlib import Path

import pytest
from PIL import Image

from tools.applets.quick_figure import (
    align_image_to_edge,
    annotate_quick,
    calculate_box_from_roi,
    export_wells,
    load_quick_csv,
    orient_image,
    register_quick_grid,
    save_quick_grid,
    set_grid_qc,
    well_rectangles,
)


def test_minimal_and_v10_compatible_csv(tmp_path):
    minimal = tmp_path / "minimal.csv"
    minimal.write_text(
        "Pos,Strain,Figure Description,Date\n1,A,PCR result,2026-08-24\n2,B,,\n",
        encoding="utf-8",
    )
    data = load_quick_csv(minimal)
    assert [item["label"] for item in data["labels"]] == ["A", "B"]
    assert data["metadata"]["figure_description"] == "PCR result"
    v10 = tmp_path / "v10.csv"
    v10.write_text("labels_strain,condition\nWT,drug\nmutant,drug\n", encoding="utf-8")
    assert load_quick_csv(v10)["labels"][1] == {"pos": 2, "label": "mutant"}


def test_quick_grid_is_durable_qc_optional_and_supports_1xn(tmp_path):
    asset = register_quick_grid("synthetic.png", (300, 100), (50, 50), (250, 50), 3)
    assert [spot["spot_id"] for spot in asset["spots"]] == ["r1c1", "r1c2", "r1c3"]
    assert asset["spots"][1]["x"] == 150
    assert asset["provenance"]["qc_status"] == "UNREVIEWED"
    accepted = set_grid_qc(asset, True, "centres checked")
    path = save_quick_grid(accepted, tmp_path / "grid.json")
    assert path.is_file() and accepted["provenance"]["qc_status"] == "ACCEPTED"


def test_roi_calculation_long_rectangles_orientation_and_export(tmp_path):
    assert calculate_box_from_roi(10, 20, 90, 180) == {"width": 80, "height": 160}
    source = Image.new("RGB", (300, 200), "white")
    assert orient_image(source, "rotate_90_cw").size == (200, 300)
    asset = register_quick_grid("synthetic.png", source.size, (60, 100), (240, 100), 3)
    boxes = well_rectangles(asset, 50, 160)
    assert boxes[0]["box"] == (35, 20, 85, 180)
    result = export_wells(
        source,
        asset,
        [{"pos": 1, "label": "A"}, {"pos": 2, "label": "B"}, {"pos": 3, "label": "C"}],
        50,
        160,
        tmp_path,
    )
    assert len(result["outputs"]) == 3
    assert all(Path(item["path"]).is_file() for item in result["outputs"])
    result2 = export_wells(
        source,
        asset,
        [{"pos": 1, "label": "A"}, {"pos": 2, "label": "B"}, {"pos": 3, "label": "C"}],
        50,
        160,
        tmp_path,
    )
    assert "quick-wells-002" in result2["outputs"][0]["path"]


def test_quick_annotation_uses_figure_description_and_rich_preset():
    source = Image.new("RGB", (300, 120), "white")
    asset = register_quick_grid("synthetic.png", source.size, (50, 60), (250, 60), 3)
    data = {
        "labels": [{"pos": i, "label": chr(64 + i)} for i in range(1, 4)],
        "metadata": {"figure_description": "PCR"},
    }
    result = annotate_quick(
        source,
        data,
        asset,
        {"in_image_enabled": True, "header_field_visibility": {"plate": False}},
    )
    assert result["preview_image"] is not None
    assert result["rendered_labels"]["header"] == ["Figure: PCR"]
    assert result["rendered_labels"]["in_image"] == ["Figure: PCR"]


def test_invalid_csv_and_out_of_bounds_fail_before_export(tmp_path):
    broken = tmp_path / "broken.csv"
    broken.write_text("Pos,Strain\n1,A\n3,B\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        load_quick_csv(broken)
    asset = register_quick_grid("synthetic.png", (100, 100), (10, 50), (90, 50), 2)
    with pytest.raises(ValueError, match="outside"):
        well_rectangles(asset, 40, 40)


def test_quick_arbitrary_edge_alignment_uses_production_convention():
    source = Image.new("RGB", (200, 100), "white")
    aligned, result = align_image_to_edge(source, (10, 20), (190, 30))
    assert aligned.size == source.size
    assert result["status"] == "ACCEPTED"
    assert result["method"] == "quick_figure_manual_horizontal_edge_line"
    assert result["angle_degrees"] > 0
