from __future__ import annotations

import ctypes
import sys

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
ERROR_ACCESS_DENIED = 5


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
