from __future__ import annotations

import ctypes
import math
import sys
from typing import Any


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def normalized_client_point(
    x: float, y: float, width: float, height: float
) -> tuple[float, float]:
    """Map any internally consistent client-coordinate domain to fractions."""
    values = tuple(float(value) for value in (x, y, width, height))
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Client coordinates and dimensions must be finite.")
    x_value, y_value, width_value, height_value = values
    if width_value <= 0 or height_value <= 0:
        raise ValueError("Client dimensions must be positive.")
    return x_value / width_value, y_value / height_value


def pointer_client_fraction(
    widget: Any, fallback_x: float, fallback_y: float
) -> tuple[float, float, str, tuple[int, int]]:
    """Read the pointer as fractions of the live canvas client rectangle.

    Fractions bridge Windows device pixels and Tk logical pixels without assuming
    either DPI domain or a monitor-specific scale factor.
    """
    if sys.platform == "win32":
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            point, bounds = _Point(), _Rect()
            handle = ctypes.c_void_p(widget.winfo_id())
            if (
                user32.GetCursorPos(ctypes.byref(point))
                and user32.ScreenToClient(handle, ctypes.byref(point))
                and user32.GetClientRect(handle, ctypes.byref(bounds))
            ):
                width = int(bounds.right - bounds.left)
                height = int(bounds.bottom - bounds.top)
                if width > 0 and height > 0:
                    x_fraction, y_fraction = normalized_client_point(
                        point.x, point.y, width, height
                    )
                    if 0 <= x_fraction < 1 and 0 <= y_fraction < 1:
                        return (
                            x_fraction,
                            y_fraction,
                            "normalized_win32_client",
                            (width, height),
                        )
        except (AttributeError, OSError, TypeError, ValueError):
            pass
    width = max(int(widget.winfo_width()), 1)
    height = max(int(widget.winfo_height()), 1)
    x_fraction, y_fraction = normalized_client_point(
        float(widget.canvasx(fallback_x)),
        float(widget.canvasy(fallback_y)),
        width,
        height,
    )
    return x_fraction, y_fraction, "normalized_tk_client", (width, height)
