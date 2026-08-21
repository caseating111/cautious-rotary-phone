from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tools import project_layout
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools import run_one_plate_validation as one_plate_validation
    from tools import standard_pillow_preview
    from tools.output_processing_records import write_output_records
    from tools.workflow_controller import Controller, PILLOW_JOBS, PROJECT_CSV_FILES
except ModuleNotFoundError:
    import project_layout
    import run_existing_pillow_from_config as pillow_adapter
    import run_one_plate_validation as one_plate_validation
    import standard_pillow_preview
    from output_processing_records import write_output_records
    from workflow_controller import Controller, PILLOW_JOBS, PROJECT_CSV_FILES


STANDARD_OUTPUT_TYPES = {
    "matrices": "matrices",
    "all-strains": "all strains",
    "label-individual": "labelled individual crops",
}


class ExtendedController(Controller):
    def __init__(self) -> None:
        super().__init__()
        self.preview_standard_outputs = tk.BooleanVar(value=True)
        self.project_prefix = tk.StringVar(value=project_layout.default_prefix())

        project_frame = ttk.Frame(self)
        project_frame.grid(row=18, column=0, columnspan=3, sticky="ew", padx=5, pady=(6, 3))
        ttk.Label(project_frame, text="Project prefix").pack(side="left")
        ttk.Entry(project_frame, textvariable=self.project_prefix, width=18).pack(side="left", padx=(6, 8))
        ttk.Button(
            project_frame,
            text="Create project layout from Image root",
            command=self.initialize_project_layout,
        ).pack(side="left")
        ttk.Label(
            project_frame,
            text="  default: dd.mm.yy; custom text such as ATTEMPT1 is allowed",
        ).pack(side="left")

        separator = ttk.Separator(self)
        separator.grid(row=19, column=0, columnspan=3, sticky="ew", padx=5, pady=6)
        ttk.Button(
            self,
            text="Custom matrices",
            command=lambda: self.launch_python("tools/custom_matrix_gui_recorded.py"),
        ).grid(row=20, column=0, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self,
            text="Preferred WT source",
            command=lambda: self.launch_python("tools/dedup_control_gui.py"),
        ).grid(row=20, column=1, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self,
            text="Open Processing Logs",
            command=self.open_processing_logs,
        ).grid(row=20, column=2, sticky="ew", padx=5, pady=3)

        ttk.Checkbutton(
            self,
            text="Preview first when a standard Pillow job will create multiple images",
            variable=self.preview_standard_outputs,
        ).grid(row=21, column=0, columnspan=3, sticky="w", padx=5, pady=(3, 6))

        ttk.Button(
            self,
            text="Run one-plate full-column proof (first pending image only)",
            command=self.run_one_plate_validation,
        ).grid(row=22, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 6))

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

        # Keep folder selection convenient, but route all actual moves through the
        # same confirmation path as the explicit project-layout button.
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

    def run_one_plate_validation(self) -> None:
        if not self.save():
            return

        self.status.set("Refreshing authoritative pending list and preparing one-plate proof…")
        self.update_idletasks()
        ahk_was_running = bool(self.ahk_process and self.ahk_process.poll() is None)
        ahk = Path(self.vars["ahk_executable"].get().strip())
        started_ahk_here = False
        if ahk.is_file() and not ahk_was_running:
            self.start_ahk()
            started_ahk_here = bool(self.ahk_process and self.ahk_process.poll() is None)

        try:
            selected = one_plate_validation.run()
        except SystemExit as exc:
            if started_ahk_here:
                self.stop_ahk()
            messagebox.showerror("One-plate validation", str(exc))
            self.status.set("One-plate proof was not launched; authoritative prepare-only results remain available.")
            return

        filename = selected.get("Filename", "")
        context = "/".join(
            value for value in (selected.get("Experiment", ""), selected.get("Set", ""), selected.get("Type", "")) if value
        )
        self.status.set(f"One-plate full-column proof launched: {filename} | {context}")
        messagebox.showinfo(
            "One-plate validation",
            f"Launched exactly one pending source:\n{filename}\n\nContext: {context or 'not specified'}\n\n"
            "Prepare-only refreshed the normal full pending list/configured macro. The proof uses a separate one-row CSV and separate macro copy, so the normal batch remains complete rather than being truncated to this plate.",
        )

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
            # This route has experiment-dependent biology/user intent. Never let the
            # base controller silently use the legacy script's inherited E2/A choice.
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
