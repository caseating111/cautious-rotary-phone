from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULTS = {
    "fiji_executable": "",
    "ahk_executable": "",
    "image_root": "",
    "crop_output": "",
    "matrix_output": "",
    "grid_csv": "",
    "images_csv": "",
    "condition_order_csv": "",
}

PILLOW_JOBS = {
    "Matrices": "matrices",
    "All strains": "all-strains",
    "All strains (extra WT removed)": "all-strains-dedup",
    "Label individual crops": "label-individual",
}


def load_config() -> dict[str, str]:
    data = DEFAULTS.copy()
    if CONFIG_FILE.exists():
        try:
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key in data:
                    if key in loaded:
                        data[key] = str(loaded[key])
        except (OSError, json.JSONDecodeError):
            pass
    return data


def save_config(data: dict[str, str]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class Controller(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Plate workflow controller")
        self.resizable(False, False)
        self.vars = {key: tk.StringVar(value=value) for key, value in load_config().items()}
        self.pillow_job = tk.StringVar(value="Matrices")
        self.ahk_process: subprocess.Popen | None = None
        self.status = tk.StringVar(value=self.environment_text())
        self.build_ui()

    def environment_text(self) -> str:
        conda = os.environ.get("CONDA_DEFAULT_ENV")
        if conda:
            return f"Python: {sys.executable} | conda: {conda}"
        return f"Python: {sys.executable}"

    def build_ui(self) -> None:
        pad = {"padx": 5, "pady": 3}
        rows = [
            ("Fiji executable", "fiji_executable", "file"),
            ("AutoHotkey v2", "ahk_executable", "file"),
            ("Image root", "image_root", "dir"),
            ("Crop output", "crop_output", "dir"),
            ("Matrix output", "matrix_output", "dir"),
            ("grid.csv", "grid_csv", "file"),
            ("images.csv", "images_csv", "file"),
            ("condition_order.csv", "condition_order_csv", "file"),
        ]

        for row, (label, key, kind) in enumerate(rows):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(self, textvariable=self.vars[key], width=60).grid(row=row, column=1, **pad)
            ttk.Button(self, text="…", width=3, command=lambda k=key, t=kind: self.browse(k, t)).grid(row=row, column=2, **pad)

        r = len(rows)
        ttk.Button(self, text="Save config", command=self.save).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Validate CSVs", command=self.validate_csvs).grid(row=r, column=1, sticky="w", **pad)
        ttk.Button(self, text="ROI presets", command=lambda: self.launch_python("tools/roi_preset_gui.py")).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", padx=5, pady=6)
        r += 1

        buttons = [
            ("Synthetic test plate", "fiji/create_synthetic_grid_plate.ijm"),
            ("Full-column alignment", "fiji/full_column_alignment.ijm"),
            ("Global visibility", "fiji/apply_global_visibility.ijm"),
        ]
        for col, (label, macro) in enumerate(buttons):
            ttk.Button(self, text=label, command=lambda m=macro: self.launch_fiji_macro(m)).grid(row=r, column=col, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Run full-column batch", command=self.run_full_column_batch).grid(row=r, column=0, columnspan=3, sticky="ew", **pad)

        r += 1
        ttk.Label(self, text="Pillow output").grid(row=r, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.pillow_job, values=list(PILLOW_JOBS), state="readonly", width=34).grid(row=r, column=1, sticky="w", **pad)
        ttk.Button(self, text="Run", command=self.run_pillow_job).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Start alignment hotkeys", command=self.start_ahk).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Stop alignment hotkeys", command=self.stop_ahk).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(self, text="Open config folder", command=self.open_config_folder).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Label(self, textvariable=self.status, wraplength=720).grid(row=r, column=0, columnspan=3, sticky="w", **pad)

    def browse(self, key: str, kind: str) -> None:
        current = self.vars[key].get().strip()
        if kind == "dir":
            chosen = filedialog.askdirectory(initialdir=current or None)
        else:
            chosen = filedialog.askopenfilename(initialdir=str(Path(current).parent) if current else None)
        if chosen:
            self.vars[key].set(chosen)

    def save(self) -> None:
        save_config({key: var.get().strip() for key, var in self.vars.items()})
        self.status.set(f"Saved: {CONFIG_FILE}")

    def validate_csvs(self) -> None:
        paths = [
            self.vars["grid_csv"].get().strip(),
            self.vars["images_csv"].get().strip(),
            self.vars["condition_order_csv"].get().strip(),
        ]
        if not all(paths):
            messagebox.showerror("CSV validation", "Select grid.csv, images.csv and condition_order.csv first.")
            return

        validator = REPO_ROOT / "tools" / "validate_project_csvs.py"
        result = subprocess.run(
            [sys.executable, str(validator), *paths],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout + result.stderr).strip() or "No validator output."
        if result.returncode == 0:
            messagebox.showinfo("CSV validation", output)
            self.status.set("CSV structure and cross-file mappings valid.")
        else:
            messagebox.showerror("CSV validation", output)
            self.status.set("CSV validation found issues.")

    def fiji_executable(self) -> Path | None:
        raw = self.vars["fiji_executable"].get().strip()
        path = Path(raw) if raw else None
        if not path or not path.is_file():
            messagebox.showerror("Fiji", "Select the Fiji/ImageJ executable first.")
            return None
        return path

    def launch_fiji_macro(self, relative_macro: str) -> None:
        exe = self.fiji_executable()
        if exe is None:
            return
        macro = REPO_ROOT / relative_macro
        if not macro.is_file():
            messagebox.showerror("Fiji", f"Macro not found:\n{macro}")
            return
        self.save()
        try:
            subprocess.Popen([str(exe), "-macro", str(macro)])
        except OSError as exc:
            messagebox.showerror("Fiji launch", str(exc))
            return
        self.status.set(f"Launched Fiji macro: {macro.name}")

    def launch_python(self, relative_script: str, *args: str) -> None:
        script = REPO_ROOT / relative_script
        if not script.is_file():
            messagebox.showerror("Python helper", f"Script not found:\n{script}")
            return
        self.save()
        try:
            subprocess.Popen([sys.executable, str(script), *args])
        except OSError as exc:
            messagebox.showerror("Python helper", str(exc))
            return
        self.status.set(f"Launched: {script.name}")

    def run_full_column_batch(self) -> None:
        ahk = Path(self.vars["ahk_executable"].get().strip())
        if ahk.is_file() and (not self.ahk_process or self.ahk_process.poll() is not None):
            self.start_ahk()
        self.launch_python("tools/run_full_column_batch_from_config.py")

    def run_pillow_job(self) -> None:
        alias = PILLOW_JOBS[self.pillow_job.get()]
        self.launch_python("tools/run_existing_pillow_from_config.py", alias)

    def start_ahk(self) -> None:
        if self.ahk_process and self.ahk_process.poll() is None:
            self.status.set("Alignment hotkeys are already running.")
            return
        exe_raw = self.vars["ahk_executable"].get().strip()
        exe = Path(exe_raw) if exe_raw else None
        script = REPO_ROOT / "ahk" / "full_column_alignment_hotkeys.ah2"
        if not exe or not exe.is_file():
            messagebox.showerror("AutoHotkey", "Select the AutoHotkey v2 executable first.")
            return
        try:
            self.ahk_process = subprocess.Popen([str(exe), str(script)])
        except OSError as exc:
            messagebox.showerror("AutoHotkey", str(exc))
            return
        self.status.set("Alignment hotkeys started.")

    def stop_ahk(self) -> None:
        if self.ahk_process and self.ahk_process.poll() is None:
            self.ahk_process.terminate()
            self.ahk_process = None
            self.status.set("Alignment hotkeys stopped.")
        else:
            self.status.set("No controller-started hotkey process is running.")

    def open_config_folder(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(APP_DIR)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            self.status.set(str(APP_DIR))


if __name__ == "__main__":
    Controller().mainloop()
