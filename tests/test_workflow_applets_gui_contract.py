from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.applets.culture_crop_export import culture_crop_signature
from tools.applets.plate_crop import calibrate_crop_size, place_plate_crop
from tools.quick_figure_gui import QuickImageCanvas
from tools.workflow_applets_gui import (
    ImageCanvas,
    WorkflowApp,
    fitted_image_geometry,
    next_image_uid,
    next_pending_image_uid,
    pending_selected_uids,
    stage_is_terminal,
)


def test_image_canvas_maps_actual_rendered_item_to_source_pixels() -> None:
    class Image:
        width = 2047
        height = 2047
        size = (2047, 2047)

    class Viewer:
        image = Image()
        offset = (100.0, 50.0)
        scale_x = 0.5
        scale_y = 0.5
        coordinate_source = "not_sampled"
        coordinate_client_dimensions = (0, 0)
        coordinate_provenance = {}
        render_canvas_size = (820, 560)
        image_item = 7
        render_generation = 3

        class Canvas:
            @staticmethod
            def winfo_width():
                return 820

            @staticmethod
            def winfo_height():
                return 560

            @staticmethod
            def bbox(_item):
                return (100, 24, 612, 536)

            @staticmethod
            def canvasx(value):
                return value

            @staticmethod
            def canvasy(value):
                return value

        canvas = Canvas()

    viewer = Viewer()
    event_x = 100 + 874 / 2047 * 512
    event_y = 24 + 1004 / 2047 * 512
    assert ImageCanvas.canvas_to_image(viewer, event_x, event_y) == pytest.approx(
        (874.0, 1004.0)
    )
    assert viewer.coordinate_source == "tk_canvas_image_item_to_source_pixels"
    assert viewer.coordinate_client_dimensions == (512, 512)
    assert viewer.coordinate_provenance["render_generation"] == 3


def test_quick_canvas_uses_the_same_image_item_mapping() -> None:
    class Image:
        width = 2047
        height = 2047
        size = (2047, 2047)

    class Canvas:
        @staticmethod
        def winfo_width():
            return 820

        @staticmethod
        def winfo_height():
            return 560

        @staticmethod
        def bbox(_item):
            return (100, 24, 612, 536)

        @staticmethod
        def canvasx(value):
            return value

        @staticmethod
        def canvasy(value):
            return value

    viewer = SimpleNamespace(
        image=Image(),
        canvas=Canvas(),
        image_item=7,
        render_generation=3,
        offset=(100.0, 50.0),
        scale=0.5,
        render_canvas_size=(820, 560),
    )
    event_x = 100 + 874 / 2047 * 512
    event_y = 24 + 1004 / 2047 * 512
    assert QuickImageCanvas._point(
        viewer, SimpleNamespace(x=event_x, y=event_y)
    ) == pytest.approx(
        (874.0, 1004.0)
    )


def test_2047_source_calibration_and_placement_remain_in_source_pixels() -> None:
    class Canvas:
        @staticmethod
        def bbox(_item):
            return (120, 24, 632, 536)

        @staticmethod
        def canvasx(value):
            return value

        @staticmethod
        def canvasy(value):
            return value

    source_size = (2047, 2047)

    def event_for(source_x: float, source_y: float) -> tuple[float, float]:
        return (
            120 + source_x / source_size[0] * 512,
            24 + source_y / source_size[1] * 512,
        )

    from tools.v10_independent.image_canvas_coordinates import image_item_to_source

    source_points = [
        image_item_to_source(Canvas(), 7, source_size, *event_for(*point))[0]
        for point in ((150, 500), (1900, 500), (500, 100), (500, 1850))
    ]
    assert all(point is not None for point in source_points)
    calibration = calibrate_crop_size(
        *source_points,
        accepted=True,
        rounding_enabled=True,
        rounding_direction="down",
        increment=50,
        source_dimensions=source_size,
    )
    assert calibration["measured_extents"]["measured_width"] == 1750
    assert calibration["measured_extents"]["measured_height"] == 1750
    assert calibration["side_pixels"] == 1750

    anchors = [
        image_item_to_source(Canvas(), 7, source_size, *event_for(*point))[0]
        for point in ((120, 400), (400, 140))
    ]
    crop = place_plate_crop(
        calibration,
        anchors[0],
        anchors[1],
        {"width": 2047, "height": 2047, "image_uid": "I1"},
    )
    assert crop["crop_box"] == {
        "x": 120,
        "y": 140,
        "width": 1750,
        "height": 1750,
        "left": 120,
        "top": 140,
        "right": 1870,
        "bottom": 1890,
    }


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


def test_manual_queue_filters_terminal_state_and_preserves_selected_order() -> None:
    images = {
        "i1": {"orientation": {"status": "ACCEPTED"}},
        "i2": {"orientation": {"status": "STALE"}},
        "i3": {"orientation": {"status": "SKIPPED"}},
        "i4": {},
    }
    assert pending_selected_uids(
        images, ["i4", "i1", "i2", "i3"], "orientation"
    ) == ["i4", "i2"]
    assert pending_selected_uids(images, ["i1", "i3"], "orientation") == []


def test_culture_terminal_state_requires_matching_saved_settings() -> None:
    signature = culture_crop_signature(
        tier="Unprocessed",
        source_kind="cropped",
        states=("Top", "Low"),
        columns=(1, 2),
        crop_width=130,
        crop_height=546,
    )
    record = {"culture": {"status": "SKIPPED", "signature": signature}}
    assert stage_is_terminal(record, "culture", signature=signature)
    changed = {**signature, "crop_width": 140}
    assert not stage_is_terminal(record, "culture", signature=changed)
    assert not stage_is_terminal(record, "culture")


def test_review_off_creates_internal_setup_preview(monkeypatch) -> None:
    class Variable:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    class Workflow:
        calls = 0

        def preview_setup(self, **_options):
            self.calls += 1
            return {"images": [], "summary": {}}

    shown = []
    errors = []
    monkeypatch.setattr(
        "tools.workflow_applets_gui.messagebox.showerror",
        lambda *args, **kwargs: errors.append((args, kwargs)),
    )
    app = SimpleNamespace(
        setup_preview=None,
        setup_signature=None,
        setup_review=Variable(False),
        _run=lambda action: action(),
        _show_setup_result=shown.append,
    )
    workflow = Workflow()
    signature = ("C:/project/1. a. Raw", True, "yyyy.mm.dd")
    assert WorkflowApp._ensure_setup_preview(app, workflow, signature)
    assert workflow.calls == 1
    assert app.setup_signature == signature
    assert shown == [app.setup_preview]
    assert not errors
    assert WorkflowApp._ensure_setup_preview(app, workflow, signature)
    assert workflow.calls == 1

    app.setup_preview = None
    app.setup_review = Variable(True)
    assert not WorkflowApp._ensure_setup_preview(app, workflow, signature)
    assert workflow.calls == 1
    assert errors


def test_fitted_canvas_geometry_maps_exact_rendered_pixels() -> None:
    shown, scales, offset = fitted_image_geometry((2048, 1999), (851, 700))
    assert shown == (717, 700)
    assert scales == (717 / 2048, 700 / 1999)
    assert offset == (67.0, 0.0)


def test_crop_calibration_presets_are_functionally_selectable(monkeypatch) -> None:
    class Variable:
        def __init__(self, value=""):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    class Widget:
        def __init__(self):
            self.options = {}

        def configure(self, **options):
            self.options.update(options)

    calibrations = {
        "plate-1700": {
            "side_pixels": 1700,
            "rounding_enabled": True,
            "rounding_increment": 50,
            "rounding_direction": "down",
            "margin_value": 0,
            "margin_unit": "pixels",
        },
        "plate-1750": {
            "side_pixels": 1750,
            "rounding_enabled": False,
            "rounding_increment": 25,
            "rounding_direction": "nearest",
            "margin_value": 10,
            "margin_unit": "pixels",
        },
    }
    selected = []
    workflow = SimpleNamespace(
        state={
            "crop_calibrations": calibrations,
            "active_crop_calibration_id": "plate-1750",
        },
        select_crop_calibration=selected.append,
    )
    monkeypatch.setattr("tools.workflow_applets_gui.load_last", lambda *_args: {})
    monkeypatch.setattr("tools.workflow_applets_gui.save_last", lambda *_args: None)
    app = SimpleNamespace(
        workflow=workflow,
        crop_calibration_box=Widget(),
        crop_calibration_id=Variable(),
        crop_rounding_enabled=Variable(),
        crop_rounding_increment=Variable(),
        crop_rounding_direction=Variable(),
        crop_margin_value=Variable(),
        crop_margin_unit=Variable(),
        crop_exact_side=Variable(),
        calibration_label=Widget(),
        status=Variable(),
        _run=lambda action: action(),
    )
    app._apply_crop_calibration_selection = lambda calibration_id: (
        WorkflowApp._apply_crop_calibration_selection(app, calibration_id)
    )
    WorkflowApp._refresh_crop_calibration_presets(app)
    assert app.crop_calibration_box.options["values"] == list(calibrations)
    assert app.crop_calibration_id.get() == "plate-1750"
    assert app.crop_rounding_increment.get() == "25"
    assert app.crop_margin_value.get() == "10"
    assert selected == ["plate-1750"]


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
    assert '"Treeview"' in text
    assert '"Listbox"' in text

    quick_text = (
        Path(__file__).resolve().parents[1] / "tools" / "quick_figure_gui.py"
    ).read_text(encoding="utf-8")
    assert "allow_detach=False" in quick_text
    assert '"Treeview"' in quick_text
    assert '"Listbox"' in quick_text
