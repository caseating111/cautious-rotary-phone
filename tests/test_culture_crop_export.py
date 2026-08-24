import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from tools.applets.culture_crop_export import (
    build_crop_records,
    export_culture_crops,
    plan_culture_crop_export,
)
from tools.grid_coordinates import build_grid_coordinate_asset


def validate_contract(instance, schema):
    for field in schema["required"]:
        assert field in instance, f"missing schema field: {field}"
    if instance.get("status") == "ACCEPTED":
        assert instance.get("preview_only") is False, (
            "accepted result must declare preview_only=false"
        )


def asset(width=300, height=700):
    refs = {
        "r1c1": {"x": 80, "y": 180},
        "r1clast": {"x": 220, "y": 180},
        "r5c1": {"x": 80, "y": 300},
        "r5clast": {"x": 220, "y": 300},
    }
    return build_grid_coordinate_asset(
        image_ref="session/plate.png",
        image_width=width,
        image_height=height,
        grid_rows=8,
        grid_cols=10,
        reference_points=refs,
        image_uid="img-1",
    )


def layout():
    labels = lambda prefix: [{"pos": c, "label": f"{prefix}{c}"} for c in range(1, 11)]
    return {
        "contract_version": 1,
        "layout_id": "L1",
        "grid_rows": 8,
        "grid_cols": 10,
        "vertical_labels": [{"pos": r, "label": f"R{r}"} for r in range(1, 9)],
        "strain_bands": [
            {"order": 1, "row_start": 1, "row_end": 4, "labels": labels("A")},
            {"order": 2, "row_start": 5, "row_end": 8, "labels": labels("B")},
        ],
    }


def metadata():
    return {"exp": "E1", "set": "S1", "type": "YPDA"}


def test_fiji_top_low_factors_and_rounding_match():
    records = build_crop_records(
        asset(), layout(), metadata(), columns=(1, 10), crop_width=10, crop_height=10
    )
    top, low = records[0], records[2]
    assert top["representative_row"] == pytest.approx(2.5)
    assert low["representative_row"] == pytest.approx(6.5)
    assert top["centre"]["y"] == pytest.approx(225.0)
    assert low["centre"]["y"] == pytest.approx(345.0)
    assert top["rectangle"]["left"] == 75
    assert low["rectangle"]["top"] == 340
    assert top["filename"].endswith("_Top_A1.png")
    assert low["filename"].endswith("_Low_B1.png")


def test_bounds_fail_before_any_output(tmp_path):
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    bad = asset(width=300, height=700)
    bad["reference_points"]["r1c1"]["x"] = 1
    bad["reference_points"]["r1c1"]["y"] = 1
    with pytest.raises(ValueError, match="source bounds"):
        plan_culture_crop_export(
            source,
            bad,
            layout(),
            metadata(),
            tmp_path / "out",
            tier="Unprocessed",
            crop_width=130,
            crop_height=546,
        )
    assert not (tmp_path / "out").exists()


def test_export_is_numbered_idempotent_and_tiers_are_distinct(tmp_path):
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    root = tmp_path / "crops"
    plan = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        root,
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    result = export_culture_crops(plan)
    assert result["status"] == "ACCEPTED"
    again = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        root,
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    assert again["status"] == "UNCHANGED_CURRENT"
    processed = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        tmp_path / "processed",
        tier="Processed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    assert processed["tier"] == "Processed"
    assert processed["output_directory"] != plan["output_directory"]


def layout_one_band(columns=12):
    return {
        "contract_version": 1,
        "layout_id": "L12",
        "grid_rows": 8,
        "grid_cols": columns,
        "vertical_labels": [{"pos": r, "label": f"R{r}"} for r in range(1, 9)],
        "strain_bands": [
            {
                "order": 1,
                "row_start": 1,
                "row_end": 8,
                "labels": [{"pos": c, "label": f"S{c}"} for c in range(1, columns + 1)],
            }
        ],
    }


def test_one_band_8x12_and_skewed_first_interior_last_centres():
    refs = {
        "r1c1": {"x": 40, "y": 100},
        "r1clast": {"x": 280, "y": 130},
        "r5c1": {"x": 70, "y": 340},
        "r5clast": {"x": 330, "y": 390},
    }
    value = build_grid_coordinate_asset(
        image_ref="one/plate.png",
        image_width=500,
        image_height=800,
        grid_rows=8,
        grid_cols=12,
        reference_points=refs,
    )
    records = build_crop_records(
        value,
        layout_one_band(),
        metadata(),
        states=("Top",),
        columns=(1, 6, 12),
        crop_width=10,
        crop_height=10,
    )
    assert records[0]["centre"] == pytest.approx({"x": 51.25, "y": 190.0})
    assert records[1]["centre"]["x"] == pytest.approx(163.75)
    assert records[1]["centre"]["y"] == pytest.approx(207.04545454545453)
    assert records[2]["centre"] == pytest.approx({"x": 298.75, "y": 227.5})
    assert all(
        record["filename"].endswith(f"_Top_S{column}.png")
        for record, column in zip(records, (1, 6, 12))
    )


def test_two_band_repeated_labels_use_band_local_positions():
    repeated = layout()
    for band in repeated["strain_bands"]:
        band["labels"] = [{"pos": c, "label": "WT"} for c in range(1, 11)]
    records = build_crop_records(
        asset(), repeated, metadata(), columns=(1,), crop_width=10, crop_height=10
    )
    assert records[0]["strain_label"] == records[1]["strain_label"] == "WT"
    assert records[0]["strain_band_order"] == 1
    assert records[1]["strain_band_order"] == 2
    assert records[0]["crop_id"] != records[1]["crop_id"]


def test_imagej_half_rounding_including_negative_half():
    from tools.applets.culture_crop_export import _imagej_round

    assert [_imagej_round(value) for value in (0.5, 1.5, -0.5, -1.5)] == [1, 2, 0, -1]


def test_output_dimensions_source_hash_and_source_unchanged(tmp_path):
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    root = tmp_path / "out"
    plan = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        root,
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    result = export_culture_crops(plan)
    assert result["source_sha256"] == before
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    crop = result["crops"][0]
    assert crop["rectangle"]["width"] == crop["rectangle"]["height"] == 10
    with Image.open(root / "Run 001" / crop["filename"]) as image:
        assert image.size == (10, 10)


def test_changed_grid_asset_creates_new_numbered_run(tmp_path):
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    root = tmp_path / "out"
    first = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        root,
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    export_culture_crops(first)
    changed = asset()
    changed["reference_points"]["r1c1"]["x"] += 1
    second = plan_culture_crop_export(
        source,
        changed,
        layout(),
        metadata(),
        root,
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    assert second["status"] == "PROPOSED"
    assert second["output_directory"].endswith("Run 002")


def test_plan_and_accepted_result_validate_against_strict_schema(tmp_path):
    schema = json.loads(
        Path("contracts/culture_crop_export.schema.json").read_text(encoding="utf-8")
    )
    source = tmp_path / "plate.png"
    Image.new("L", (300, 700), 100).save(source)
    plan = plan_culture_crop_export(
        source,
        asset(),
        layout(),
        metadata(),
        tmp_path / "out",
        tier="Unprocessed",
        states=("Top",),
        columns=(1,),
        crop_width=10,
        crop_height=10,
    )
    validate_contract(plan, schema)
    result = export_culture_crops(plan)
    # Expected current failure: exporter omits required preview_only on ACCEPTED results.
    validate_contract(result, schema)
