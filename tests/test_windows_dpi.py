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
def test_synthetic_canvas_pointer_round_trip_uses_original_image_pixels() -> None:
    code = """
import ctypes, json, tkinter as tk
from ctypes import wintypes
from PIL import Image
from tools.workflow_applets_gui import ImageCanvas

root = tk.Tk()
root.geometry('900x650+20+20')
root.attributes('-alpha', 0.0)
viewer = ImageCanvas(root)
viewer.pack(fill='both', expand=True)
viewer.show(Image.new('L', (2047, 2047), 0))
root.update()
user32 = ctypes.windll.user32
old = wintypes.POINT()
user32.GetCursorPos(ctypes.byref(old))
client_rect = wintypes.RECT()
user32.GetClientRect(viewer.canvas.winfo_id(), ctypes.byref(client_rect))
client_width = client_rect.right - client_rect.left
client_height = client_rect.bottom - client_rect.top
mapped = []
try:
    for target_x, target_y in ((150.0, 300.0), (1850.0, 1700.0)):
        tk_x = viewer.offset[0] + target_x * viewer.scale_x
        tk_y = viewer.offset[1] + target_y * viewer.scale_y
        client = wintypes.POINT(
            round(tk_x / viewer.canvas.winfo_width() * client_width),
            round(tk_y / viewer.canvas.winfo_height() * client_height),
        )
        user32.ClientToScreen(viewer.canvas.winfo_id(), ctypes.byref(client))
        user32.SetCursorPos(client.x, client.y)
        root.update()
        mapped.append(viewer.canvas_to_image(1.0, 1.0))
finally:
    user32.SetCursorPos(old.x, old.y)
    source = viewer.coordinate_source
    root.destroy()
print(json.dumps({'mapped': mapped, 'source': source}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout.strip())
    assert data["source"] == "normalized_win32_client"
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
