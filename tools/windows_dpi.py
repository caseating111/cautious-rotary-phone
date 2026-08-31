from __future__ import annotations

import ctypes
import math
import sys
from typing import Any


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
ERROR_ACCESS_DENIED = 5


def coordinate_scale_from_dpi(window_dpi: float, tk_pixels_per_inch: float) -> float:
    """Convert Tk pointer coordinates into the window's rendered-pixel space."""
    values = (float(window_dpi), float(tk_pixels_per_inch))
    if not all(math.isfinite(value) and value > 0 for value in values):
        return 1.0
    ratio = values[0] / values[1]
    return ratio if 0.5 <= ratio <= 4.0 else 1.0


def tk_coordinate_scale(widget: Any) -> float:
    """Return the live Windows-DPI/Tk-DPI ratio for a Tk widget."""
    if sys.platform != "win32":
        return 1.0
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        getter = user32.GetDpiForWindow
        getter.argtypes = [ctypes.c_void_p]
        getter.restype = ctypes.c_uint
        window_dpi = float(getter(ctypes.c_void_p(widget.winfo_id())))
        tk_pixels_per_inch = float(widget.winfo_fpixels("1i"))
    except (AttributeError, OSError, TypeError, ValueError):
        return 1.0
    return coordinate_scale_from_dpi(window_dpi, tk_pixels_per_inch)


def pointer_client_coordinates(
    widget: Any, fallback_x: float, fallback_y: float
) -> tuple[float, float, str]:
    """Read pointer coordinates in the widget's rendered device-pixel space."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            point = _Point()
            if user32.GetCursorPos(ctypes.byref(point)) and user32.ScreenToClient(
                ctypes.c_void_p(widget.winfo_id()), ctypes.byref(point)
            ):
                width = int(widget.winfo_width())
                height = int(widget.winfo_height())
                if 0 <= point.x < width and 0 <= point.y < height:
                    return float(point.x), float(point.y), "win32_device_pixels"
        except (AttributeError, OSError, TypeError, ValueError):
            pass
    scale = tk_coordinate_scale(widget)
    return (
        float(widget.canvasx(fallback_x)) * scale,
        float(widget.canvasy(fallback_y)) * scale,
        "tk_event_dpi_reconciled",
    )


def enable_per_monitor_v2() -> str:
    """Set Windows DPI awareness before the first Tk window is created."""
    if sys.platform != "win32":
        return "NOT_WINDOWS"
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = ctypes.c_bool
        ctypes.set_last_error(0)
        if setter(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)):
            return "PER_MONITOR_V2"
        error = ctypes.get_last_error()
        if error == ERROR_ACCESS_DENIED:
            return "ALREADY_CONFIGURED"
        return f"FAILED_{error}"
    except (AttributeError, OSError):
        try:
            if ctypes.windll.user32.SetProcessDPIAware():
                return "SYSTEM_AWARE_FALLBACK"
        except (AttributeError, OSError):
            pass
        return "UNAVAILABLE"
