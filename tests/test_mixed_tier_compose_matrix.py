import sys
import types
from pathlib import Path

sys.modules.setdefault("pandas", types.ModuleType("pandas"))

import pytest
from PIL import Image

from tools.applets.annotation import compose_matrix


def layout():
    return {
        "rows": ["WT", "Mutant"],
        "cols": ["0h", "24h"],
        "tile_size": (20, 20),
        "padding": 2,
    }


def items(tmp_path: Path):
    top = tmp_path / "top.png"
    low = tmp_path / "low.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(top)
    Image.new("RGB", (8, 8), (0, 0, 255)).save(low)
    return [
        {"image": str(top), "strain": "WT", "condition": "0h", "tier": "Top"},
        {"image": str(low), "strain": "Mutant", "condition": "24h", "tier": "Low"},
    ]


def test_mixed_tiers_preview_has_exact_placed_count_and_writes_nothing(tmp_path: Path):
    result = compose_matrix(items(tmp_path), layout())
    assert result["status"] == "PREVIEW"
    assert result["tile_count"] == 2
    assert result["preview_image"] is not None
    assert not list(tmp_path.glob("*.matrix-*"))


def test_validation_happens_before_output_publish(tmp_path: Path):
    output = tmp_path / "out.png"
    bad = items(tmp_path) + [
        {
            "image": str(tmp_path / "missing.png"),
            "strain": "WT",
            "condition": "24h",
            "tier": "Low",
        }
    ]
    with pytest.raises(FileNotFoundError):
        compose_matrix(bad, layout(), output)
    assert not output.exists()


@pytest.mark.parametrize(
    "bad_layout",
    [
        {"rows": [], "cols": ["0h"]},
        {"rows": ["WT", "WT"], "cols": ["0h"]},
        {"rows": ["WT"], "cols": ["0h"], "tile_size": (0, 20)},
    ],
)
def test_layout_validation(bad_layout):
    with pytest.raises(ValueError):
        compose_matrix([], bad_layout)


def test_invalid_tier_duplicate_cell_and_unknown_cell_fail(tmp_path: Path):
    source = items(tmp_path)[0]
    for bad in [
        [dict(source, tier="middle")],
        [source, dict(source, tier="Low")],
        [dict(source, strain="Unknown")],
    ]:
        with pytest.raises(ValueError):
            compose_matrix(bad, layout())


def test_atomic_publish_and_source_crops_unchanged(tmp_path: Path):
    source_items = items(tmp_path)
    before = {Path(item["image"]).read_bytes() for item in source_items}
    output = tmp_path / "nested" / "matrix.png"
    result = compose_matrix(source_items, layout(), output)
    assert result["status"] == "COMPOSED"
    assert result["output_path"] == str(output.resolve())
    assert result["tile_count"] == 2
    assert output.is_file()
    assert {Path(item["image"]).read_bytes() for item in source_items} == before
    assert not list(output.parent.glob(".matrix-*.tmp"))
