from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
PENDING_IMAGES_CSV = APP_DIR / "pending_images.csv"
PREFLIGHT_REPORT = APP_DIR / "last_preflight.txt"
CONFIGURED_BATCH_MACRO = APP_DIR / "batch_full_column.configured.ijm"
CONFIGURED_LEGACY_BATCH_MACRO = APP_DIR / "batch_four_point_fallback.configured.ijm"

DEFAULTS = {
    "fiji_executable": "",
    "ahk_executable": "",
    "image_root": "",
    "crop_output": "",
    "matrix_output": "",
    "grid_csv": "",
    "images_csv": "",
    "condition_order_csv": "",
    "alignment_tolerance": "0.08",
    "crop_width": "130",
    "crop_height": "546",
    "visibility_band": "50",
    "visibility_black_offset": "3",
    "visibility_high_percentile": "99.5",
}

PROJECT_CSV_FILES = {
    "grid_csv": "grid.csv",
    "images_csv": "images.csv",
    "condition_order_csv": "condition_order.csv",
}

PILLOW_JOBS = {
    "Matrices": "matrices",
    "All strains": "all-strains",
    "All strains (extra WT removed)": "all-strains-dedup",
    "Label individual crops": "label-individual",
}

PROCESSING_SETTINGS = [
    ("Alignment peak tolerance", "alignment_tolerance"),
    ("Crop width", "crop_width"),
    ("Crop height", "crop_height"),
    ("Visibility outside band", "visibility_band"),
    ("Visibility black offset", "visibility_black_offset"),
    ("Visibility high percentile", "visibility_high_percentile"),
]


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


def sibling_project_csvs(selected: Path) -> dict[str, Path]:
    folder = selected.parent
    return {
        key: candidate
        for key, name in PROJECT_CSV_FILES.items()
        if (candidate := folder / name).is_file()
    }


def preflight_dialog_text(returncode: int, pending: int, output: str, report_exists: bool) -> str:
    if returncode == 0:
        if pending:
            summary = f"Ready for batch alignment.\n\nPending images: {pending}"
        else:
            summary = "Preflight is clean. No images are currently pending."
        if report_exists:
            summary += f"\n\nFull details are saved to:\n{PREFLIGHT_REPORT}"
        return summary

    if report_exists:
        return (
            "Preflight found blocking items.\n\n"
            "Open the saved preflight report for the full actionable list:\n"
            f"{PREFLIGHT_REPORT}"
        )
    return output or "Batch preflight failed without a saved report or error message."


def preparation_error_text(output: str, report_exists: bool) -> str:
    if report_exists and "BATCH PREFLIGHT" in output:
        return (
            "Batch preparation stopped at preflight.\n\n"
            "Open the saved preflight report for the full actionable list:\n"
            f"{PREFLIGHT_REPORT}"
        )
    return output


class Controller(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Image workflow controller")
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
        ttk.Button(self, text="Metadata review", command=lambda: self.launch_python("tools/metadata_review_gui.py")).grid(row=r, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(self, text="Processing settings", command=self.open_processing_settings).grid(row=r, column=2, sticky="ew", **pad)
        r += 1
        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", padx=5, pady=6)
        r += 1

        ttk.Button(self, text="Synthetic test plate", command=lambda: self.launch_fiji_macro("fiji/create_synthetic_grid_plate.ijm")).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Full-column alignment", command=lambda: self.launch_fiji_macro("fiji/full_column_alignment.ijm")).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(self, text="Global visibility", command=lambda: self.launch_configured_fiji("visibility")).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Batch preflight", command=self.run_batch_preflight).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Run full-column batch", command=self.run_full_column_batch).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(self, text="Run 4-point fallback", command=self.run_four_point_batch).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Label(self, text="Pillow output").grid(row=r, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.pillow_job, values=list(PILLOW_JOBS), state="readonly", width=34).grid(row=r, column=1, sticky="w", **pad)
        ttk.Button(self, text="Run", command=self.run_pillow_job).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Start alignment hotkeys", command=self.start_ahk).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Stop alignment hotkeys", command=self.stop_ahk).grid(row=r, column=1, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Open last preflight report", command=self.open_preflight_report).grid(row=r, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(self, text="Open config folder", command=self.open_config_folder).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Button(self, text="Open image root", command=lambda: self.open_path_from_config("image_root")).grid(row=r, column=0, sticky="ew", **pad)
        ttk.Button(self, text="Open crop output", command=lambda: self.open_path_from_config("crop_output")).grid(row=r, column=1, sticky="ew", **pad)
        ttk.Button(self, text="Open matrix output", command=lambda: self.open_path_from_config("matrix_output")).grid(row=r, column=2, sticky="ew", **pad)

        r += 1
        ttk.Label(self, textvariable=self.status, wraplength=720).grid(row=r, column=0, columnspan=3, sticky="w", **pad)

    def browse(self, key: str, kind: str) -> None:
        current = self.vars[key].get().strip()
        if kind == "dir":
            chosen = filedialog.askdirectory(initialdir=current or None)
        else:
            chosen = filedialog.askopenfilename(initialdir=str(Path(current).parent) if current else None)
        if not chosen:
            return

        self.vars[key].set(chosen)
        if key in PROJECT_CSV_FILES:
            filled = 0
            for sibling_key, sibling_path in sibling_project_csvs(Path(chosen)).items():
                if sibling_key == key or self.vars[sibling_key].get().strip():
                    continue
                self.vars[sibling_key].set(str(sibling_path))
                filled += 1
            if filled:
                self.status.set(f"Found {filled} sibling project CSV path(s) in the same folder.")

    def save(self) -> None:
        save_config({key: var.get().strip() for key, var in self.vars.items()})
        self.status.set(f"Saved: {CONFIG_FILE}")

    def open_processing_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Processing settings")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        pad = {"padx": 6, "pady": 4}
        for row, (label, key) in enumerate(PROCESSING_SETTINGS):
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(dialog, textvariable=self.vars[key], width=14).grid(row=row, column=1, **pad)

        def save_and_close() -> None:
            try:
                alignment_tolerance = float(self.vars["alignment_tolerance"].get())
                crop_width = int(self.vars["crop_width"].get())
                crop_height = int(self.vars["crop_height"].get())
                visibility_band = float(self.vars["visibility_band"].get())
                visibility_black_offset = float(self.vars["visibility_black_offset"].get())
                percentile = float(self.vars["visibility_high_percentile"].get())

                if not all(
                    math.isfinite(value)
                    for value in (
                        alignment_tolerance,
                        visibility_band,
                        visibility_black_offset,
                        percentile,
                    )
                ):
                    raise ValueError("Processing settings must be finite numbers.")
                if alignment_tolerance <= 0:
                    raise ValueError("Alignment tolerance must be positive.")
                if crop_width <= 0 or crop_height <= 0:
                    raise ValueError("Crop dimensions must be positive integers.")
                if visibility_band < 1:
                    raise ValueError("Visibility band must be at least 1.")
                if percentile <= 0 or percentile > 100:
                    raise ValueError("Visibility percentile must be >0 and <=100.")
            except ValueError as exc:
                messagebox.showerror("Processing settings", str(exc), parent=dialog)
                return
            self.save()
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=save_and_close).grid(row=len(PROCESSING_SETTINGS), column=0, columnspan=2, sticky="ew", **pad)

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
        result = subprocess.run([sys.executable, str(validator), *paths], capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip() or "No validator output."
        if result.returncode == 0:
            messagebox.showinfo("CSV validation", output)
            self.status.set("CSV structure and cross-file mappings valid.")
        else:
            messagebox.showerror("CSV validation", output)
            self.status.set("CSV validation found issues.")

    def batch_preflight_result(self) -> tuple[int, str, int]:
        self.save()
        script = REPO_ROOT / "tools" / "preflight_batch.py"
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip() or "No preflight output."
        pending = 0
        if PENDING_IMAGES_CSV.is_file():
            with PENDING_IMAGES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
                pending = sum(1 for _ in csv.DictReader(handle))
        return result.returncode, output, pending

    def run_batch_preflight(self) -> None:
        returncode, output, pending = self.batch_preflight_result()
        dialog = preflight_dialog_text(returncode, pending, output, PREFLIGHT_REPORT.is_file())
        if returncode == 0:
            messagebox.showinfo("Batch preflight", dialog)
            self.status.set(f"Batch preflight ready: {pending} image(s) pending.")
        else:
            messagebox.showerror("Batch preflight", dialog)
            self.status.set("Batch preflight found items to resolve. Open the saved report for easier review.")

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

    def launch_configured_fiji(self, macro_alias: str) -> None:
        script = REPO_ROOT / "tools" / "run_fiji_macro_from_config.py"
        if not script.is_file():
            messagebox.showerror("Fiji launch", f"Configured Fiji helper not found:\n{script}")
            return
        self.save()
        result = subprocess.run(
            [sys.executable, str(script), macro_alias],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            messagebox.showerror("Fiji launch", output or "Configured Fiji launch failed without a message.")
            self.status.set("Configured Fiji launch failed.")
            return
        self.status.set(f"Launched configured Fiji macro: {macro_alias}")

    def run_prepared_batch(self, legacy: bool) -> None:
        self.save()
        script = REPO_ROOT / "tools" / "run_full_column_batch_from_config.py"
        if not script.is_file():
            messagebox.showerror("Batch preparation", f"Batch helper not found:\n{script}")
            self.status.set("Batch not started: helper missing.")
            return

        args = [sys.executable, str(script), "--prepare-only"]
        configured_macro = CONFIGURED_BATCH_MACRO
        route_name = "full-column"
        if legacy:
            args.append("--legacy")
            configured_macro = CONFIGURED_LEGACY_BATCH_MACRO
            route_name = "4-point fallback"

        prepared = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (prepared.stdout + prepared.stderr).strip() or "No batch preparation output."
        if prepared.returncode != 0:
            if "All expected crops already exist" in output:
                messagebox.showinfo("Batch", output)
                self.status.set("Batch already complete.")
            else:
                messagebox.showerror(
                    "Batch preparation",
                    preparation_error_text(output, PREFLIGHT_REPORT.is_file()),
                )
                self.status.set(f"{route_name} batch not started: preparation needs attention.")
            return

        exe = self.fiji_executable()
        if exe is None:
            self.status.set(f"{route_name} batch prepared, but Fiji is not configured.")
            return
        if not configured_macro.is_file():
            messagebox.showerror("Batch preparation", f"Prepared macro not found:\n{configured_macro}")
            self.status.set(f"{route_name} batch not started: prepared macro missing.")
            return

        ahk_was_running = bool(self.ahk_process and self.ahk_process.poll() is None)
        ahk = Path(self.vars["ahk_executable"].get().strip())
        if ahk.is_file() and not ahk_was_running:
            self.start_ahk()
        started_ahk_here = not ahk_was_running and bool(self.ahk_process and self.ahk_process.poll() is None)

        try:
            subprocess.Popen([str(exe), "-macro", str(configured_macro)])
        except OSError as exc:
            if started_ahk_here:
                self.stop_ahk()
            messagebox.showerror("Fiji launch", str(exc))
            self.status.set(f"{route_name} batch prepared but Fiji launch failed.")
            return
        self.status.set(f"Prepared {route_name} batch launched in Fiji.")

    def run_full_column_batch(self) -> None:
        self.run_prepared_batch(legacy=False)

    def run_four_point_batch(self) -> None:
        self.run_prepared_batch(legacy=True)

    def run_pillow_job(self) -> None:
        alias = PILLOW_JOBS[self.pillow_job.get()]
        script = REPO_ROOT / "tools" / "run_existing_pillow_from_config.py"
        if not script.is_file():
            messagebox.showerror("Pillow output", f"Pillow helper not found:\n{script}")
            self.status.set("Pillow output not started: helper missing.")
            return

        self.save()
        self.status.set(f"Running Pillow output: {self.pillow_job.get()}…")
        self.update_idletasks()
        result = subprocess.run(
            [sys.executable, str(script), alias],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            messagebox.showerror("Pillow output", output or "Pillow output failed without a message.")
            self.status.set("Pillow output failed; see the error message.")
            return

        last_line = output.splitlines()[-1] if output else "Output complete."
        self.status.set(f"Pillow output complete: {last_line}")

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

    def open_preflight_report(self) -> None:
        self.open_existing_path(PREFLIGHT_REPORT, "Preflight report")

    def open_existing_path(self, path: Path, label: str) -> None:
        if not path.exists():
            messagebox.showerror(label, f"Not found:\n{path}")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            self.status.set(str(path))

    def open_path_from_config(self, key: str) -> None:
        raw = self.vars[key].get().strip()
        path = Path(raw) if raw else None
        if not path or not path.is_dir():
            messagebox.showerror("Open folder", f"Configured folder does not exist:\n{raw or '(not set)'}")
            return
        self.open_existing_path(path, "Open folder")

    def open_config_folder(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.open_existing_path(APP_DIR, "Open config folder")


if __name__ == "__main__":
    Controller().mainloop()
