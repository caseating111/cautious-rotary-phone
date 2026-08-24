from __future__ import annotations

import json

import pytest

from tools import applet_presets


def test_last_used_and_named_presets_round_trip(tmp_path) -> None:
    store = tmp_path / "presets.json"
    applet_presets.save_last("culture crop", {"width": 180, "height": 600}, path=store)
    applet_presets.save_preset(
        "culture crop", "Long PCR", {"width": 180, "height": 600}, path=store
    )

    assert applet_presets.load_last("culture_crop", path=store) == {
        "width": 180,
        "height": 600,
    }
    assert applet_presets.list_presets("culture crop", path=store) == ["Long PCR"]
    assert (
        applet_presets.load_preset("culture_crop", "Long PCR", path=store)["height"]
        == 600
    )


def test_store_is_valid_atomic_json_and_colors_are_reusable(tmp_path) -> None:
    store = tmp_path / "presets.json"
    applet_presets.save_custom_color("336699", path=store)
    applet_presets.save_custom_color("#336699", path=store)
    assert applet_presets.custom_colors(path=store) == ["#336699"]
    assert json.loads(store.read_text(encoding="utf-8"))["format_version"] == 1
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("value", ["", "#12345", "#GG0000"])
def test_invalid_colors_fail_clearly(value, tmp_path) -> None:
    with pytest.raises(ValueError, match="RRGGBB"):
        applet_presets.save_custom_color(value, path=tmp_path / "presets.json")
