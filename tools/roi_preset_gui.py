from __future__ import annotations

import json
import math
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path.home() / ".cautious-rotary-phone"
PRESETS_FILE = APP_DIR / "roi_presets.json"
ACTIVE_FILE = APP_DIR / "active_roi_preset.txt"
CONFIG_FILE = APP_DIR / "config.json"

PATCH_FUNCTION = r'''
function loadActiveRectPreset() {
    presetFile = getDirectory("home") + ".cautious-rotary-phone" + File.separator + "active_roi_preset.txt";
    if (!File.exists(presetFile)) return;

    presetText = File.openAsString(presetFile);
    presetLines = split(presetText, "\n");

    for (presetI = 0; presetI < presetLines.length; presetI++) {
        presetLine = replace(presetLines[presetI], "\r", "");
        if (startsWith(presetLine, "width="))
            rotRectWidth = parseFloat(substring(presetLine, 6));
        else if (startsWith(presetLine, "height="))
            rotRectHeight = parseFloat(substring(presetLine, 7));
        else if (startsWith(presetLine, "angle="))
            rotRectAngle = parseFloat(substring(presetLine, 6));
    }
}
'''.strip()

HELPER_MARKER = "// ----------- Helper functions -----------------//"
TOOL_MARKER = 'macro "Rotated Rectangle Click Tool - Cf00R11cc" {'
PATCH_CALL = "\tloadActiveRectPreset();"
TOOLSET_NAME = "Roi 1-Click Tools.ijm"


def ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def validated_preset(preset: dict) -> dict[str, float]:
    try:
        width = float(preset["width"])
        height = float(preset["height"])
        angle = float(preset.get("angle", 0))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Preset width, height and angle must be numeric: {exc}") from exc
    if not all(math.isfinite(value) for value in (width, height, angle)):
        raise ValueError("Preset width, height and angle must be finite numbers.")
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive.")
    return {"width": width, "height": height, "angle": angle}


def read_active() -> dict[str, float]:
    values: dict[str, str] = {}
    if not ACTIVE_FILE.exists():
        return {}
    try:
        text = ACTIVE_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in {"width", "height", "angle"}:
            values[key] = value.strip()
    if not {"width", "height"}.issubset(values):
        return {}
    try:
        return validated_preset(values)
    except ValueError:
        return {}


def write_active(preset: dict[str, float]) -> None:
    clean = validated_preset(preset)
    ensure_dir()
    ACTIVE_FILE.write_text(
        f"width={clean['width']}\nheight={clean['height']}\nangle={clean['angle']}\n",
        encoding="utf-8",
    )


def load_presets() -> dict[str, dict[str, float]]:
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}

    clean: dict[str, dict[str, float]] = {}
    for name, preset in data.items():
        if not isinstance(name, str) or not isinstance(preset, dict):
            continue
        try:
            clean[name] = validated_preset(preset)
        except ValueError:
            continue
    return clean


def save_presets(presets: dict[str, dict[str, float]]) -> None:
    ensure_dir()
    PRESETS_FILE.write_text(json.dumps(presets, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def configured_fiji_root(config_path: Path = CONFIG_FILE) -> Path | None:
    if not config_path.is_file():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = str(data.get("fiji_executable", "")).strip()
    if not raw:
        return None
    executable = Path(raw)
    return executable.parent if executable.parent.is_dir() else None


def find_roi_click_tools(fiji_root: Path | None) -> list[Path]:
    if fiji_root is None or not fiji_root.is_dir():
        return []

    likely = [
        fiji_root / "macros" / "toolsets" / TOOLSET_NAME,
        fiji_root / "plugins" / TOOLSET_NAME,
    ]
    found = [path for path in likely if path.is_file()]
    if found:
        return sorted(set(path.resolve() for path in found))

    return sorted(set(path.resolve() for path in fiji_root.rglob(TOOLSET_NAME) if path.is_file()))


def patch_roi_click_tools(path: Path) -> Path | None:
    text = path.read_text(encoding="utf-8")
    if "function loadActiveRectPreset()" in text and PATCH_CALL in text:
        return None
    if HELPER_MARKER not in text or TOOL_MARKER not in text:
        raise ValueError("This does not look like the expected ROI 1-Click Tools macro source.")

    backup = path.with_suffix(path.suffix + ".before-roi-presets.bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    text = text.replace(HELPER_MARKER, HELPER_MARKER + "\n\n" + PATCH_FUNCTION, 1)
    text = text.replace(TOOL_MARKER, TOOL_MARKER + "\n\n" + PATCH_CALL, 1)
    path.write_text(text, encoding="utf-8")
    return backup


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ROI presets")
        self.resizable(False, False)
        self.presets = load_presets()

        self.name = tk.StringVar()
        self.width = tk.StringVar(value="108")
        self.height = tk.StringVar(value="108")
        self.angle = tk.StringVar(value="0")

        pad = {"padx": 6, "pady": 4}
        ttk.Label(self, text="Preset").grid(row=0, column=0, sticky="w", **pad)
        self.combo = ttk.Combobox(self, textvariable=self.name, width=24)
        self.combo.grid(row=0, column=1, columnspan=2, **pad)
        self.combo.bind("<<ComboboxSelected>>", self.load_selected)

        for row, (label, variable) in enumerate(
            [("Width", self.width), ("Height", self.height), ("Angle", self.angle)], start=1
        ):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(self, textvariable=variable, width=12).grid(row=row, column=1, sticky="w", **pad)

        ttk.Button(self, text="Import captured ROI", command=self.import_capture).grid(row=4, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Button(self, text="Save preset", command=self.save_current).grid(row=5, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Activate", command=self.activate).grid(row=5, column=1, sticky="ew", **pad)
        ttk.Button(self, text="Delete", command=self.delete_current).grid(row=5, column=2, sticky="ew", **pad)
        ttk.Separator(self).grid(row=6, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Patch ROI 1-Click Tools…", command=self.patch_plugin).grid(row=7, column=0, columnspan=3, sticky="ew", **pad)

        self.status = tk.StringVar(value=f"Active file: {ACTIVE_FILE}")
        ttk.Label(self, textvariable=self.status, wraplength=360).grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        self.refresh_names()

    def refresh_names(self) -> None:
        self.combo["values"] = sorted(self.presets)

    def current_values(self) -> dict[str, float]:
        return validated_preset(
            {
                "width": self.width.get(),
                "height": self.height.get(),
                "angle": self.angle.get(),
            }
        )

    def load_selected(self, _event=None) -> None:
        preset = self.presets.get(self.name.get())
        if not preset:
            return
        self.width.set(str(preset["width"]))
        self.height.set(str(preset["height"]))
        self.angle.set(str(preset.get("angle", 0)))

    def import_capture(self) -> None:
        values = read_active()
        if not {"width", "height"}.issubset(values):
            messagebox.showinfo("No capture", f"Run fiji/roi_preset_capture.ijm on an active rectangle ROI first.\n\n{ACTIVE_FILE}")
            return
        self.width.set(str(values["width"]))
        self.height.set(str(values["height"]))
        self.angle.set(str(values.get("angle", 0)))
        self.status.set("Captured ROI loaded. Give it a name, then Save preset.")

    def save_current(self) -> None:
        name = self.name.get().strip()
        if not name:
            messagebox.showerror("Preset name", "Enter a preset name.")
            return
        try:
            self.presets[name] = self.current_values()
        except ValueError as exc:
            messagebox.showerror("Invalid preset", str(exc))
            return
        save_presets(self.presets)
        self.refresh_names()
        self.status.set(f"Saved preset: {name}")

    def activate(self) -> None:
        name = self.name.get().strip()
        try:
            preset = self.presets.get(name) or self.current_values()
            write_active(preset)
        except ValueError as exc:
            messagebox.showerror("Invalid preset", str(exc))
            return
        self.status.set(f"Active: {name or 'unsaved'} — {preset['width']} x {preset['height']}")

    def delete_current(self) -> None:
        name = self.name.get().strip()
        if name in self.presets:
            del self.presets[name]
            save_presets(self.presets)
            self.name.set("")
            self.refresh_names()
            self.status.set(f"Deleted preset: {name}")

    def patch_plugin(self) -> None:
        candidates = find_roi_click_tools(configured_fiji_root())
        selected = str(candidates[0]) if len(candidates) == 1 else ""

        if not selected:
            selected = filedialog.askopenfilename(
                title="Select Roi 1-Click Tools.ijm",
                filetypes=[("ImageJ macro", "*.ijm"), ("All files", "*.*")],
            )
        if not selected:
            return
        try:
            backup = patch_roi_click_tools(Path(selected))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Patch failed", str(exc))
            return

        if backup is None:
            messagebox.showinfo(
                "Already patched",
                f"ROI 1-Click Tools is already preset-aware.\n\nToolset: {selected}",
            )
            self.status.set(f"ROI 1-Click Tools already patched: {selected}")
            return

        messagebox.showinfo(
            "Patched",
            "ROI 1-Click Tools will now read the active rectangle preset before each rectangle click.\n\n"
            f"Toolset: {selected}\nBackup: {backup}\n\nRestart/reload the toolset once.",
        )
        self.status.set(f"ROI 1-Click Tools patched: {selected}")


if __name__ == "__main__":
    ensure_dir()
    App().mainloop()
