from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError:
    np = None
import pytest
from PIL import Image

from tools.applets.annotation import (
    derive_annotation_positions,
    normalize_annotation_preset,
    preview_plate_annotation,
    write_annotation_result,
)
from tools.applets.visibility import (
    adjust_plate_visibility,
    apply_visibility_adjustment,
    write_visibility_result,
)
from tools.grid_coordinates import build_grid_coordinate_asset


def asset():
    refs = {
        "r1c1": {"x": 20, "y": 20},
        "r1clast": {"x": 100, "y": 20},
        "r5c1": {"x": 20, "y": 60},
        "r5clast": {"x": 100, "y": 60},
    }
    return build_grid_coordinate_asset(
        image_ref="plate.png",
        image_width=140,
        image_height=100,
        grid_rows=8,
        grid_cols=10,
        reference_points=refs,
    )


def layout():
    return {
        "contract_version": 1,
        "layout_id": "L1",
        "grid_rows": 8,
        "grid_cols": 10,
        "vertical_labels": [{"pos": row, "label": f"R{row}"} for row in range(1, 9)],
        "strain_bands": [
            {
                "order": 1,
                "row_start": 1,
                "row_end": 8,
                "local_grid_cols": 10,
                "labels": [
                    {"pos": column, "label": f"S{column}"} for column in range(1, 11)
                ],
            }
        ],
    }


def request():
    return {
        "contract_version": 1,
        "image_uid": "img-1",
        "layout_id": "L1",
        "labels": {"plate": "P1"},
    }


@pytest.mark.skipif(np is None, reason="numpy unavailable outside workflow-c")
def test_unknown_visibility_preset_fails_closed():
    with pytest.raises(ValueError, match="Unknown visibility preset"):
        adjust_plate_visibility(Image.new("L", (140, 100)), asset(), "not-a-preset")


@pytest.mark.skipif(np is None, reason="numpy unavailable outside workflow-c")
def test_visibility_output_and_sidecar_support_bare_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source.png"
    Image.fromarray(np.full((100, 140), 100, dtype=np.uint8)).save(source)
    result = adjust_plate_visibility(
        source, asset(), options={"image_uid": "img-1", "status": "ACCEPTED"}
    )
    assert result["grid_asset_id"] == asset()["asset_id"]
    output = apply_visibility_adjustment(source, result, "processed.png")
    assert Path(output).is_file()
    sidecar = write_visibility_result(result, "processed.json")
    assert Path(sidecar).is_file()


def test_annotation_preview_is_in_memory_and_request_is_validated():
    result = preview_plate_annotation(
        Image.new("L", (140, 100)), layout(), asset(), request()
    )
    assert result["preview_image"] is not None
    assert result["output_path"] is None
    assert result["placements"]["vertical_placements"][0]["label"] == "R1"
    assert "rendered_box" in result["placements"]["vertical_placements"][0]
    with pytest.raises(ValueError):
        preview_plate_annotation(
            Image.new("L", (140, 100)), layout(), asset(), {"labels": {}}
        )


def test_annotation_sidecar_is_atomic(tmp_path):
    result = {"contract_version": 1, "status": "ACCEPTED", "output_path": "out.png"}
    path = write_annotation_result(result, str(tmp_path / "nested" / "result.json"))
    assert Path(path).is_file()
    assert not list((tmp_path / "nested").glob("*.tmp"))


def test_annotation_label_sets_have_independent_colours_and_two_axis_offsets():
    preset = normalize_annotation_preset(
        {
            "strain_color": "#112233",
            "vertical_color": "#445566",
            "strain_offset_x": 7,
            "vertical_offset_y": 9,
        }
    )
    positions = derive_annotation_positions(layout(), asset(), preset)
    baseline = derive_annotation_positions(
        layout(), asset(), normalize_annotation_preset()
    )
    assert (
        positions["strain_placements"][0]["x"]
        == baseline["strain_placements"][0]["x"] + 7
    )
    assert (
        positions["vertical_placements"][0]["y"]
        == baseline["vertical_placements"][0]["y"] + 9
    )
    assert preset["strain_color"] == "#112233"
    assert preset["vertical_color"] == "#445566"
