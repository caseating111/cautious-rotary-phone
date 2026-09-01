from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tools.windows_dpi import normalized_client_point, pointer_client_fraction


def test_normalized_client_point_cancels_coordinate_domain_scale() -> None:
    logical = normalized_client_point(537, 276, 820, 560)
    physical = normalized_client_point(1074, 552, 1640, 1120)
    assert logical == physical


def test_pointer_fraction_has_a_safe_tk_fallback(monkeypatch) -> None:
    class Canvas:
        def canvasx(self, value):
            return value + 3

        def canvasy(self, value):
            return value + 4

        def winfo_width(self):
            return 200

        def winfo_height(self):
            return 100

    monkeypatch.setattr("tools.windows_dpi.sys.platform", "other")
    assert pointer_client_fraction(Canvas(), 10, 20) == (
        13 / 200,
        24 / 100,
        "normalized_tk_client",
        (200, 100),
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows client-fraction contract")
def test_synthetic_canvas_image_item_round_trip_uses_original_image_pixels() -> None:
    code = """
import json, tkinter as tk
from PIL import Image
from tools.workflow_applets_gui import ImageCanvas

root = tk.Tk()
root.geometry('900x650+20+20')
root.attributes('-alpha', 0.0)
viewer = ImageCanvas(root)
viewer.pack(fill='both', expand=True)
viewer.show(Image.new('L', (2047, 2047), 0))
root.update()
mapped = []
for target_x, target_y in ((150.0, 300.0), (1850.0, 1700.0)):
    tk_x, tk_y = viewer.image_to_canvas(target_x, target_y)
    mapped.append(viewer.canvas_to_image(tk_x, tk_y))
source = viewer.coordinate_source
provenance = viewer.current_coordinate_provenance()
root.destroy()
print(json.dumps({'mapped': mapped, 'source': source, 'provenance': provenance}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout.strip())
    assert data["source"] == "tk_canvas_image_item_to_source_pixels"
    assert data["provenance"]["source_dimensions"] == [2047, 2047]
    for actual, expected in zip(
        data["mapped"], ((150.0, 300.0), (1850.0, 1700.0)), strict=True
    ):
        assert actual == pytest.approx(expected, abs=2.0)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows UI scaling contract")
def test_workflow_app_does_not_force_per_monitor_v2() -> None:
    code = """
import ctypes, json
from tools.workflow_applets_gui import WorkflowApp

root = WorkflowApp()
root.withdraw()
context = ctypes.windll.user32.GetWindowDpiAwarenessContext(root.winfo_id())
is_per_monitor_v2 = bool(
    ctypes.windll.user32.AreDpiAwarenessContextsEqual(
        context, ctypes.c_void_p(-4)
    )
)
root.destroy()
print(json.dumps({'per_monitor_v2': is_per_monitor_v2}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout.strip()) == {"per_monitor_v2": False}
