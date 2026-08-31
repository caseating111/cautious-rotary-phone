from __future__ import annotations

from pathlib import Path

from tools.workflow_applets_gui import (
    fitted_image_geometry,
    next_image_uid,
    next_pending_image_uid,
)


def test_next_image_progression_is_ordered_and_stops_at_end() -> None:
    image_uids = ["i1", "i2", "i3"]
    assert next_image_uid(image_uids, "i1") == "i2"
    assert next_image_uid(image_uids, "i2") == "i3"
    assert next_image_uid(image_uids, "i3") is None
    assert next_image_uid(image_uids, "missing") is None


def test_next_pending_progression_skips_terminal_images_and_wraps() -> None:
    images = {
        "i1": {"orientation": {"status": "ACCEPTED"}},
        "i2": {"orientation": {"status": "SKIPPED"}},
        "i3": {},
    }
    assert next_pending_image_uid(images, "i1", "orientation") == "i3"
    assert next_pending_image_uid(images, "i3", "orientation") is None
    images["i1"]["orientation"]["status"] = "STALE"
    assert next_pending_image_uid(images, "i3", "orientation") == "i1"
    assert next_pending_image_uid(images, "i1", "culture") == "i2"


def test_fitted_canvas_geometry_maps_exact_rendered_pixels() -> None:
    shown, scales, offset = fitted_image_geometry((2048, 1999), (851, 700))
    assert shown == (717, 700)
    assert scales == (717 / 2048, 700 / 1999)
    assert offset == (67.0, 0.0)


def test_repeated_stage_hotkeys_and_help_are_wired() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "workflow_applets_gui.py"
    ).read_text(encoding="utf-8")
    for key, action in (
        ('"x": self.start_orientation', "orientation start"),
        ('"v": self.preview_orientation', "orientation preview"),
        ('"z": self.accept_orientation', "orientation accept"),
        ('"c": self.skip_orientation', "orientation skip"),
        ('"x": self.start_crop_placement', "crop start"),
        ('"v": self.preview_crop', "crop preview"),
        ('"z": self.accept_crop', "crop accept"),
        ('"c": self.skip_crop', "crop skip"),
    ):
        assert key in text, action
    assert "Keyboard shortcuts" in text
    assert "Shortcuts are ignored while typing in a field." in text
    assert "Automatically advance to the next image" in text
