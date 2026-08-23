from __future__ import annotations

import os
import tkinter as tk
import subprocess
import sys
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tools import project_csv_discovery
    from tools import project_layout
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools import run_one_plate_validation as one_plate_validation
    from tools import standard_pillow_preview
    from tools.output_processing_records import write_output_records
    from tools.workflow_controller import Controller, PILLOW_JOBS, PROJECT_CSV_FILES, REPO_ROOT
except ModuleNotFoundError:
    import project_csv_discovery
    import project_layout
    import run_existing_pillow_from_config as pillow_adapter
    import run_one_plate_validation as one_plate_validation
    import standard_pillow_preview
    from output_processing_records import write_output_records
    from workflow_controller import Controller, PILLOW_JOBS, PROJECT_CSV_FILES, REPO_ROOT


APP_RUNTIME_DIR = Path.home() / ".cautious-rotary-phone"
ACTIVE_BATCH_FILE = APP_RUNTIME_DIR / "four_point_batch.active"
CONTROL_REQUEST_FILE = APP_RUNTIME_DIR / "four_point_control.request"
RESUME_MARKER_FILE = APP_RUNTIME_DIR / "four_point_resume.marker"
OWNED_FIJI_PIDS_FILE = APP_RUNTIME_DIR / "four_point_owned_fiji_pids.txt"
CLOSE_REQUEST_FILE = APP_RUNTIME_DIR / "controller_close.request"

def active_batch_marker() -> bool:
    """Return true only for a live runner; discard stale crash leftovers."""
    try:
        pid = int(ACTIVE_BATCH_FILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
    except (FileNotFoundError, OSError, ValueError):
        try:
            ACTIVE_BATCH_FILE.unlink()
        except FileNotFoundError:
            pass
        return False
    return True

def owned_fiji_pids() -> set[int]:
    try:
        return {int(line) for line in OWNED_FIJI_PIDS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}
    except (FileNotFoundError, ValueError):
        return set()


def terminate_owned_fiji(pid: int) -> None:
    probe = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False)
    if "fiji-windows-x64.exe" not in probe.stdout.casefold():
        return
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)

STANDARD_OUTPUT_TYPES = {
    "matrices": "matrices",
    "all-strains": "all strains",
    "label-individual": "labelled individual crops",
}


class ExtendedController(Controller):
    def __init__(self) -> None:
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.close_controller)
        self.preview_standard_outputs = tk.BooleanVar(value=self.config_bool("preview_standard_outputs", True))
        self.replace_existing_crops = tk.BooleanVar(value=self.config_bool("replace_existing_crops", False))
        self.skip_done = tk.BooleanVar(value=self.config_bool("skip_done", True))
        self.clear_fiji_on_cancel = tk.BooleanVar(value=self.config_bool("clear_fiji_on_cancel", True))
        self.batch_grid_qc = tk.BooleanVar(value=self.config_bool("batch_grid_qc", True))
        self.hide_source_during_alignment = tk.BooleanVar(value=self.config_bool("hide_source_during_alignment", True))
        self.batch_subfolder = tk.StringVar()
        self.project_prefix = tk.StringVar(value=project_layout.default_prefix())
        self.fiji_processes: list[subprocess.Popen] = []
        for variable in (self.preview_standard_outputs, self.replace_existing_crops, self.skip_done, self.clear_fiji_on_cancel, self.batch_grid_qc, self.hide_source_during_alignment):
            variable.trace_add("write", self.save_toggle_settings)


        self.build_extended_ui()

    def build_extended_ui(self) -> None:
        """Arrange existing actions by workflow stage without changing their commands."""
        def button(parent: tk.Misc, text: str, command, border_color: str = "#a8a8a8", **kwargs) -> tk.Frame:
            frame = tk.Frame(parent, background=border_color, borderwidth=0, highlightthickness=0)
            inner = tk.Button(frame, text=text, command=command, relief="flat", borderwidth=0, highlightthickness=0, background="#f2f2f2", activebackground="#e4e4e4", padx=10, pady=5, takefocus=0, **kwargs)
            inner.pack(fill="both", expand=True, padx=1, pady=1)
            frame.inner_button = inner
            return frame

        for child in self.winfo_children():
            child.destroy()

        self.columnconfigure(0, weight=1)
        title_bar = ttk.Frame(self)
        title_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        title_bar.columnconfigure(1, weight=1)
        ttk.Label(title_bar, text="Image workflow controller").grid(row=0, column=0, sticky="w")
        self.save_header_button = button(title_bar, text="Save config", command=lambda: self.save(explicit=True))
        self.save_header_button.grid(row=0, column=2, padx=(8, 5))
        self.reboot_header_button = button(title_bar, text="Reboot", command=self.reboot_controller)
        self.reboot_header_button.grid(row=0, column=3, sticky="e")

        header = ttk.Frame(self)
        header.grid(row=1, column=0, sticky="ew", padx=5)
        self.tab_container = ttk.Frame(self)
        self.tab_container.grid(row=2, column=0, sticky="nsew", padx=5)
        self.tab_container.columnconfigure(0, weight=1)
        self.tab_container.rowconfigure(0, weight=1)
        self.setup_tab = ttk.Frame(self.tab_container)
        self.align_tab = ttk.Frame(self.tab_container)
        self.outputs_tab = ttk.Frame(self.tab_container)
        self.settings_tab = ttk.Frame(self.tab_container)
        self.tab_frames = {
            "setup": self.setup_tab,
            "align": self.align_tab,
            "outputs": self.outputs_tab,
            "settings": self.settings_tab,
        }
        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")
        self.tab_buttons: dict[str, tk.Frame] = {}
        for column, (key, label) in enumerate((
            ("setup", "1. Setup"),
            ("align", "2. Align & Export"),
            ("outputs", "3. Outputs"),
            ("settings", "Settings"),
        )):
            tab_button = button(header, text=label, command=lambda k=key: self.select_tab(k), border_color="#666666")
            tab_button.grid(row=0, column=column, padx=(0, 3))
            self.tab_buttons[key] = tab_button


        pad = {"padx": 5, "pady": 3}
        ttk.Label(self.setup_tab, text="Project files and readiness").grid(row=0, column=0, columnspan=3, sticky="w", **pad)
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
        for row, (label, key, kind) in enumerate(rows, start=1):
            ttk.Label(self.setup_tab, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(self.setup_tab, textvariable=self.vars[key], width=60).grid(row=row, column=1, **pad)
            button(self.setup_tab, text="…", width=3, command=lambda k=key, t=kind: self.browse(k, t)).grid(row=row, column=2, **pad)
        setup_actions = ttk.Frame(self.setup_tab)
        setup_actions.grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        button(setup_actions, text="Choose CSV folder and find project CSVs", command=self.choose_csv_folder).pack(side="left")
        button(setup_actions, text="Metadata review", command=lambda: self.launch_python("tools/metadata_review_gui.py")).pack(side="left", padx=(5, 0))
        button(setup_actions, text="Save config", command=lambda: self.save(explicit=True)).pack(side="left", padx=(5, 0))
        project = ttk.Frame(self.setup_tab)
        project.grid(row=10, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(project, text="Project prefix").pack(side="left")
        ttk.Entry(project, textvariable=self.project_prefix, width=18).pack(side="left", padx=(6, 8))
        button(project, text="Create project layout from Image root", command=self.initialize_project_layout).pack(side="left")
        button(self.setup_tab, text="Reconcile / validate CSV workflow", command=self.run_batch_preflight).grid(row=11, column=0, columnspan=3, sticky="ew", **pad)

        ttk.Label(self.align_tab, text="Single plate or batch alignment and crop export").grid(row=0, column=0, sticky="w", **pad)
        actions = ttk.LabelFrame(self.align_tab, text="Run and recovery")
        actions.grid(row=1, column=0, sticky="w", **pad)
        batch_actions = ttk.Frame(actions)
        batch_actions.pack(anchor="w", padx=5, pady=(5, 2))
        button(batch_actions, text="Run all 4-point", command=self.run_all_four_point).pack(side="left")
        button(batch_actions, text="Run subfolder", command=self.run_subfolder_four_point).pack(side="left", padx=(5, 0))
        subfolders = ttk.Combobox(batch_actions, textvariable=self.batch_subfolder, state="readonly", width=28)
        subfolders.pack(side="left", padx=(5, 0))
        subfolders.configure(postcommand=lambda: self.refresh_subfolders(subfolders))
        single_actions = ttk.Frame(actions)
        single_actions.pack(anchor="w", padx=5, pady=(2, 5))
        button(single_actions, text="Run single image", command=lambda: self.run_one_plate_validation(rerun_done=False)).pack(side="left")
        button(single_actions, text="Rerun single image", command=lambda: self.run_one_plate_validation(rerun_done=True)).pack(side="left", padx=(5, 0))
        button(single_actions, text="Reset stale batch marker", command=self.reset_stale_batch_marker).pack(side="left", padx=(5, 0))

        options = ttk.LabelFrame(self.align_tab, text="Batch and alignment options")
        options.grid(row=2, column=0, sticky="w", **pad)
        ttk.Checkbutton(options, text="Skip done", variable=self.skip_done).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2))
        ttk.Checkbutton(options, text="Replace existing crops after accepted grid", variable=self.replace_existing_crops).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(options, text="Batch: show grid QC after every four clicks", variable=self.batch_grid_qc).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(options, text="Hide source image while aligning (batch + single)", variable=self.hide_source_during_alignment).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(options, text="Clear Fiji source/alignment windows on C cancellation", variable=self.clear_fiji_on_cancel).grid(row=4, column=0, sticky="w", padx=5, pady=(2, 5))

        ttk.Label(self.outputs_tab, text="Run after crop export").grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(self.outputs_tab, text="Preview first when a standard Pillow job will create multiple images", variable=self.preview_standard_outputs).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(self.outputs_tab, text="Pillow output").grid(row=2, column=0, sticky="w", **pad)
        ttk.Combobox(self.outputs_tab, textvariable=self.pillow_job, values=list(PILLOW_JOBS), state="readonly", width=34).grid(row=2, column=1, sticky="w", **pad)
        button(self.outputs_tab, text="Run", command=self.run_pillow_job).grid(row=2, column=2, sticky="ew", **pad)
        output_actions = ttk.Frame(self.outputs_tab)
        output_actions.grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        button(output_actions, text="Custom matrices", command=lambda: self.launch_python("tools/custom_matrix_gui_recorded.py")).pack(side="left")
        button(output_actions, text="Preferred WT source", command=lambda: self.launch_python("tools/dedup_control_gui.py")).pack(side="left", padx=(5, 0))
        button(self.outputs_tab, text="Open crop output", command=lambda: self.open_path_from_config("crop_output")).grid(row=4, column=0, sticky="ew", **pad)
        button(self.outputs_tab, text="Open matrix output", command=lambda: self.open_path_from_config("matrix_output")).grid(row=4, column=1, sticky="ew", **pad)
        button(self.outputs_tab, text="Open image root", command=lambda: self.open_path_from_config("image_root")).grid(row=4, column=2, sticky="ew", **pad)

        button(self.settings_tab, text="Processing settings", command=self.open_processing_settings).grid(row=0, column=0, sticky="ew", **pad)
        button(self.settings_tab, text="ROI presets", command=lambda: self.launch_python("tools/roi_preset_gui.py")).grid(row=0, column=1, sticky="ew", **pad)
        button(self.settings_tab, text="Open Processing Logs", command=self.open_processing_logs).grid(row=0, column=2, sticky="ew", **pad)
        button(self.settings_tab, text="Open last preflight report", command=self.open_preflight_report).grid(row=1, column=0, columnspan=2, sticky="ew", **pad)
        button(self.settings_tab, text="Open config folder", command=self.open_config_folder).grid(row=1, column=2, sticky="ew", **pad)

        ttk.Label(self, textvariable=self.status, wraplength=720).grid(row=3, column=0, sticky="w", padx=5, pady=(4, 5))
        self.select_tab("setup")
    def select_tab(self, key: str) -> None:
        """Show one workflow stage and give its square tab button a subtle active state."""
        self.tab_frames[key].tkraise()
        for name, tab_button in self.tab_buttons.items():
            tab_button.inner_button.configure(background="#dddddd" if name == key else "#f2f2f2")
    def _shutdown_controller(self, reboot: bool = False) -> None:
        """End only this launcher tree and Fiji PIDs recorded by this controller."""
        self.stop_ahk()
        for process in self.fiji_processes:
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        for pid in owned_fiji_pids():
            terminate_owned_fiji(pid)
        OWNED_FIJI_PIDS_FILE.unlink(missing_ok=True)
        if os.environ.get("CAUTIOUS_CONTROLLER_LAUNCHER") == "1":
            APP_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            CLOSE_REQUEST_FILE.write_text("reboot\n" if reboot else "close\n", encoding="utf-8")
        self.destroy()
        if os.environ.get("CAUTIOUS_CONTROLLER_LAUNCHER") == "1" and not reboot:
            subprocess.Popen(["taskkill", "/PID", str(os.getppid()), "/T", "/F"], creationflags=subprocess.CREATE_NO_WINDOW)

    def close_controller(self) -> None:
        self._shutdown_controller()

    def reboot_controller(self) -> None:
        if not self.save():
            return
        ahk = Path(self.vars["ahk_executable"].get().strip())
        helper = REPO_ROOT / "ahk" / "reboot_controller.ah2"
        launcher = REPO_ROOT / "start_controller.cmd"
        if not ahk.is_file() or not helper.is_file() or not launcher.is_file():
            messagebox.showerror("Reboot", "AutoHotkey v2 or the normal controller launcher is unavailable.")
            return
        subprocess.Popen([str(ahk), str(helper), str(launcher), str(os.getpid()), str(os.getppid())])
        self._shutdown_controller(reboot=True)

    def config_bool(self, key: str, default: bool) -> bool:
        value = self.vars.get(key)
        if value is None:
            return default
        return value.get().strip().casefold() in {"1", "true", "yes", "on"}

    def save_toggle_settings(self, *_args: object) -> None:
        """Persist controller choices immediately, without waiting for a run button."""
        self.save()

    def save(self, explicit: bool = False) -> bool:
        self.vars["preview_standard_outputs"].set("1" if self.preview_standard_outputs.get() else "0")
        self.vars["replace_existing_crops"].set("1" if self.replace_existing_crops.get() else "0")
        self.vars["skip_done"].set("1" if self.skip_done.get() else "0")
        self.vars["clear_fiji_on_cancel"].set("1" if self.clear_fiji_on_cancel.get() else "0")
        self.vars["batch_grid_qc"].set("1" if self.batch_grid_qc.get() else "0")
        self.vars["hide_source_during_alignment"].set("1" if self.hide_source_during_alignment.get() else "0")
        return super().save(explicit)

    def refresh_subfolders(self, widget: ttk.Combobox) -> None:
        root = Path(self.vars["image_root"].get().strip())
        values = [path.name for path in sorted(root.iterdir()) if path.is_dir()] if root.is_dir() else []
        widget.configure(values=values)
        if self.batch_subfolder.get() not in values:
            self.batch_subfolder.set("")

    def reset_stale_batch_marker(self) -> None:
        if active_batch_marker():
            messagebox.showerror(
                "Reset stale batch marker",
                "A live batch wrapper still owns this marker. Finish the batch or use C; resetting it now could allow overlapping batches.",
            )
            return
        for path in (ACTIVE_BATCH_FILE, CONTROL_REQUEST_FILE, RESUME_MARKER_FILE):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self.status.set("Cleared stale four-point batch runtime markers.")
    def run_all_four_point(self) -> None:
        self.run_four_point_batch(None)

    def run_subfolder_four_point(self) -> None:
        folder = self.batch_subfolder.get().strip()
        if not folder:
            messagebox.showerror("Run subfolder", "Choose an image-root subfolder from the dropdown first.")
            return
        self.run_four_point_batch(folder)

    def run_four_point_batch(self, subfolder: str | None) -> None:
        self.fiji_processes = [process for process in self.fiji_processes if process.poll() is None]
        if active_batch_marker():
            messagebox.showerror("Run four-point batch", "A four-point batch is still active. Finish it or use C to cancel it before starting another batch.")
            return
        # A completed macro may leave Fiji open deliberately. Its wrapper is no longer an active batch and must not block the next run.
        self.fiji_processes = []
        if not self.save():
            return
        replace_existing = self.replace_existing_crops.get()
        if not self.skip_done.get() and not replace_existing:
            messagebox.showerror(
                "Run four-point batch",
                "Processing completed plates needs accepted-grid crop replacement, which is not enabled yet. Keep Skip done selected.",
            )
            return
        script = Path(one_plate_validation.batch.__file__).resolve()
        args = [sys.executable, str(script)]
        if subfolder:
            args.extend(["--subfolder", subfolder])
        if replace_existing:
            args.append("--replace-existing-crops")

        ahk_was_running = bool(self.ahk_process and self.ahk_process.poll() is None)
        if not ahk_was_running:
            ahk = Path(self.vars["ahk_executable"].get().strip())
            if not ahk.is_file():
                messagebox.showerror("Run four-point batch", "Select the AutoHotkey v2 executable before starting an interactive batch.")
                return
            self.start_ahk()
            # Register the shell hook before Fiji can display its first dialog.
            time.sleep(0.3)
        if not self.ahk_process or self.ahk_process.poll() is not None:
            messagebox.showerror("Run four-point batch", "Alignment hotkeys did not start; batch launch was cancelled.")
            return
        try:
            batch_process = subprocess.Popen(args)
            self.fiji_processes = [process for process in self.fiji_processes if process.poll() is None]
            self.fiji_processes.append(batch_process)
        except OSError as exc:
            messagebox.showerror("Run four-point batch", str(exc))
            return
        scope = subfolder or "all pending folders"
        action = "accepted-grid crop replacement is enabled" if replace_existing else "completed plates are skipped"
        self.status.set(f"Launched four-point batch for {scope}; {action}.")

    def choose_csv_folder(self) -> None:
        initial = None
        for key in PROJECT_CSV_FILES:
            configured = self.vars[key].get().strip()
            if configured:
                initial = str(Path(configured).parent)
                break
        chosen = filedialog.askdirectory(initialdir=initial)
        if not chosen:
            return

        try:
            found = project_csv_discovery.discover_project_csvs(Path(chosen))
        except ValueError as exc:
            messagebox.showerror("Project CSV discovery", str(exc))
            self.status.set("CSV folder selected, but the three project CSVs could not be identified safely.")
            return

        for key, path in found.items():
            self.vars[key].set(str(path))

        if self.save():
            names = ", ".join(path.name for path in found.values())
            self.status.set(f"Project CSVs found and configured from {chosen}: {names}")

    def browse(self, key: str, kind: str) -> None:
        before = self.vars[key].get().strip()
        super().browse(key, kind)
        after = self.vars[key].get().strip()
        if key != "image_root" or not after or after == before:
            return

        source = Path(after)
        existing = project_layout.existing_layout_for_raw(source) if source.is_dir() else None
        if existing is not None:
            self.apply_project_layout(existing, original_parent=source.parent.parent.parent)
            self.status.set(f"Recognised existing project layout: {existing.project_root}")
            return

        self.initialize_project_layout()

    def apply_project_layout(
        self,
        layout: project_layout.ProjectLayout,
        original_parent: Path | None = None,
        moved_from: Path | None = None,
    ) -> None:
        self.vars["image_root"].set(str(layout.image_root))
        self.vars["crop_output"].set(str(layout.crop_output))
        self.vars["matrix_output"].set(str(layout.matrix_output))

        candidate_dirs = [layout.metadata_dir, layout.project_root]
        if original_parent is not None:
            candidate_dirs.append(original_parent)
        for key, filename in PROJECT_CSV_FILES.items():
            configured = self.vars[key].get().strip()
            if configured:
                if moved_from is not None:
                    rebased = project_layout.rebase_moved_path(configured, moved_from, layout.image_root)
                    if rebased != Path(configured).resolve():
                        self.vars[key].set(str(rebased))
                continue
            for folder in candidate_dirs:
                candidate = folder / filename
                if candidate.is_file():
                    self.vars[key].set(str(candidate))
                    break

        if self.save():
            self.status.set(
                f"Project ready: {layout.project_root} | raw images preserved under Raw | output paths configured automatically."
            )

    def initialize_project_layout(self) -> None:
        if self.config_load_error:
            messagebox.showerror(
                "Project layout",
                "Repair or explicitly replace the unreadable config before moving the image-root folder. "
                "This prevents a successful folder move from being followed by an unsaved path configuration.",
            )
            return

        raw = self.vars["image_root"].get().strip()
        if not raw:
            messagebox.showerror("Project layout", "Select Image root first.")
            return
        source = Path(raw).resolve()
        original_parent = source.parent

        existing = project_layout.existing_layout_for_raw(source) if source.is_dir() else None
        if existing is None:
            try:
                planned = project_layout.planned_layout(source, self.project_prefix.get())
            except SystemExit as exc:
                messagebox.showerror("Project layout", str(exc))
                return

            if not messagebox.askyesno(
                "Create project layout?",
                "Create the automatic project folders now?\n\n"
                f"Project: {planned.project_root}\n"
                f"Raw image root: {planned.image_root}\n"
                f"Crops: {planned.crop_output}\n"
                f"Matrices: {planned.matrix_output}\n"
                f"Metadata: {planned.metadata_dir}\n\n"
                "The selected image-root folder itself will be moved intact into Raw. "
                "Image files are not modified or copied. Any external shortcut that points to the old folder path will need updating.",
            ):
                self.status.set("Image root selected. Automatic project layout was not created.")
                return

        try:
            layout = project_layout.initialize_project(source, self.project_prefix.get())
        except SystemExit as exc:
            messagebox.showerror("Project layout", str(exc))
            return

        moved_from = None if layout.image_root == source else source
        self.apply_project_layout(layout, original_parent=original_parent, moved_from=moved_from)
        messagebox.showinfo(
            "Project layout",
            f"Project ready:\n{layout.project_root}\n\n"
            f"Raw images:\n{layout.image_root}\n\n"
            f"Crops:\n{layout.crop_output}\n\n"
            f"Matrices:\n{layout.matrix_output}\n\n"
            f"Metadata folder:\n{layout.metadata_dir}",
        )

    def open_processing_logs(self) -> None:
        raw = self.vars["matrix_output"].get().strip()
        folder = Path(raw) / "Processing Logs" if raw else None
        if folder is None or not folder.is_dir():
            messagebox.showinfo(
                "Processing Logs",
                "No Processing Logs folder exists yet. It is created after the first recorded output.",
            )
            return
        self.open_existing_path(folder, "Processing Logs")

    def run_one_plate_validation(self, *, rerun_done: bool = False) -> None:
        if not self.save():
            return

        image_root = self.vars["image_root"].get().strip()
        chosen = filedialog.askopenfilename(
            title=("Choose one plate to reset and re-run" if rerun_done else "Choose one pending plate for the 4-point proof"),
            initialdir=image_root or None,
            filetypes=[
                ("Plate images", "*.jpg *.jpeg *.png *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not chosen:
            self.status.set("One-plate proof cancelled before Fiji launch.")
            return

        filename = Path(chosen).name
        self.status.set(f"Refreshing pending list and preparing 4-point proof for {filename}…")
        self.update_idletasks()
        ahk_was_running = bool(self.ahk_process and self.ahk_process.poll() is None)
        ahk = Path(self.vars["ahk_executable"].get().strip())
        started_ahk_here = False
        if ahk.is_file() and not ahk_was_running:
            self.start_ahk()
            # Let the scoped helper register its shell hook/hotkeys before a
            # cold Fiji launch can display the first wait-for-user dialog.
            time.sleep(0.3)
            started_ahk_here = bool(self.ahk_process and self.ahk_process.poll() is None)

        try:
            selected, fiji_process = one_plate_validation.run_with_process(
                filename,
                rerun_done=rerun_done,
                replace_existing=self.replace_existing_crops.get(),
            )
        except SystemExit as exc:
            if started_ahk_here:
                self.stop_ahk()
            messagebox.showerror("One-plate validation", str(exc))
            self.status.set("One-plate proof was not launched; authoritative prepare-only results remain available.")
            return
        self.fiji_processes = [process for process in self.fiji_processes if process.poll() is None]
        self.fiji_processes.append(fiji_process)

        filename = selected.get("Filename", "")
        context = "/".join(
            value
            for value in (selected.get("Experiment", ""), selected.get("Set", ""), selected.get("Type", ""))
            if value
        )
        self.status.set(f"One-plate 4-point proof launched: {filename} | {context}")

    def standard_output_count(self, alias: str, config: dict) -> int:
        crop_count = None
        if alias == "label-individual":
            selected = pillow_adapter.validate_unique_crop_matches(
                Path(config["crop_output"]),
                Path(config["grid_csv"]),
                Path(config["images_csv"]),
                allow_missing=False,
            )
            crop_count = len(selected)
        return standard_pillow_preview.estimated_output_count(alias, config, crop_count=crop_count)

    def last_output_text(self) -> str | None:
        if not pillow_adapter.LAST_OUTPUT_FILE.is_file():
            return None
        try:
            value = pillow_adapter.LAST_OUTPUT_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return value or None

    def record_standard_output(self, alias: str, previous_output: str | None) -> None:
        current = self.last_output_text()
        if not current or current == previous_output:
            return
        output = Path(current)
        if not output.is_dir():
            return
        try:
            config = pillow_adapter.load_config()
            selection = standard_pillow_preview.full_matrix_selection(config)
            required = len(
                pillow_adapter.expected_crop_contract(Path(config["grid_csv"]), Path(config["images_csv"]))
            )
            available = len(
                pillow_adapter.validate_unique_crop_matches(
                    Path(config["crop_output"]),
                    Path(config["grid_csv"]),
                    Path(config["images_csv"]),
                    allow_missing=False,
                )
            )
            human_log, _machine_recipe = write_output_records(
                Path(config["matrix_output"]),
                output,
                output_type=STANDARD_OUTPUT_TYPES[alias],
                selection=selection,
                required_crops=required,
                available_crops=available,
                used_crops=available,
                display_mode="raw",
            )
        except (OSError, SystemExit) as exc:
            self.status.set(f"Output created, but its processing record could not be written: {exc}")
            return
        self.status.set(f"Pillow output complete: {output} | Processing Log: {human_log}")

    def run_standard_output(self, alias: str) -> None:
        previous = self.last_output_text()
        super().run_pillow_job()
        self.record_standard_output(alias, previous)

    def run_pillow_job(self) -> None:
        alias = PILLOW_JOBS[self.pillow_job.get()]
        if alias == "all-strains-dedup":
            self.launch_python("tools/dedup_control_gui.py")
            self.status.set("Choose the preferred WT source; that dialog previews before Top + Low output by default.")
            return

        if not self.preview_standard_outputs.get():
            self.run_standard_output(alias)
            return

        if not self.save():
            return
        preview = None
        try:
            config = pillow_adapter.load_config()
            count = self.standard_output_count(alias, config)
            if count <= 1:
                self.run_standard_output(alias)
                return

            self.status.set(f"Building one representative preview for {self.pillow_job.get()}…")
            self.update_idletasks()
            preview = standard_pillow_preview.build_preview(alias)
            self.open_existing_path(preview.image, "Pillow preview")
            accepted = messagebox.askyesno(
                "Pillow preview",
                f"One representative image has been opened.\n\n"
                f"The full job will create approximately {count} images. Generate the full output now?",
            )
        except SystemExit as exc:
            messagebox.showerror("Pillow preview", str(exc))
            self.status.set("Pillow output stopped during representative preview/check.")
            return
        finally:
            if preview is not None:
                preview.cleanup()

        if not accepted:
            self.status.set("Preview rejected. Full Pillow output was not generated.")
            return
        self.run_standard_output(alias)


def main() -> None:
    app = ExtendedController()
    app.mainloop()


if __name__ == "__main__":
    main()
