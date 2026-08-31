from __future__ import annotations

import json
import subprocess
import sys

import pytest


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
