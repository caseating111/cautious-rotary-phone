from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tools.windows_dpi import coordinate_scale_from_dpi, pointer_client_coordinates


def test_coordinate_scale_reconciles_windows_and_tk_dpi() -> None:
    assert coordinate_scale_from_dpi(192, 96) == 2.0
    assert coordinate_scale_from_dpi(192, 192) == 1.0
    assert coordinate_scale_from_dpi(144, 96) == 1.5
    assert coordinate_scale_from_dpi(0, 96) == 1.0


def test_pointer_coordinates_have_a_safe_tk_fallback(monkeypatch) -> None:
    class Canvas:
        def canvasx(self, value):
            return value + 3

        def canvasy(self, value):
            return value + 4

    monkeypatch.setattr("tools.windows_dpi.sys.platform", "other")
    assert pointer_client_coordinates(Canvas(), 10, 20) == (
        13.0,
        24.0,
        "tk_event_dpi_reconciled",
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPI contract")
def test_tk_uses_the_windows_dpi_after_awareness_is_enabled() -> None:
    code = """
import ctypes, json, tkinter as tk
from tools.windows_dpi import enable_per_monitor_v2
status = enable_per_monitor_v2()
root = tk.Tk()
root.withdraw()
tk_dpi = float(root.winfo_fpixels('1i'))
system_dpi = int(ctypes.windll.user32.GetDpiForSystem())
root.destroy()
print(json.dumps({'status': status, 'tk_dpi': tk_dpi, 'system_dpi': system_dpi}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout.strip())
    assert data["status"] in {
        "PER_MONITOR_V2",
        "ALREADY_CONFIGURED",
        "SYSTEM_AWARE_FALLBACK",
    }
    assert abs(data["tk_dpi"] - data["system_dpi"]) < 1.0
