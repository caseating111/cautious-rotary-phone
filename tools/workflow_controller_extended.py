from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools import standard_pillow_preview
    from tools.output_processing_records import write_output_records
    from tools.workflow_controller import Controller, PILLOW_JOBS
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter
    import standard_pillow_preview
    from output_processing_records import write_output_records
    from workflow_controller import Controller, PILLOW_JOBS


STANDARD_OUTPUT_TYPES = {
    "matrices": "matrices",
    "all-strains": "all strains",
    "label-individual": "labelled individual crops",
}


class ExtendedController(Controller):
    def __init__(self) -> None:
        super().__init__()
        self.preview_standard_outputs = tk.BooleanVar(value=True)

        separator = ttk.Separator(self)
        separator.grid(row=18, column=0, columnspan=3, sticky="ew", padx=5, pady=6)
        ttk.Button(
            self,
            text="Custom matrices",
            command=lambda: self.launch_python("tools/custom_matrix_gui_recorded.py"),
        ).grid(row=19, column=0, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self,
            text="Preferred WT source",
            command=lambda: self.launch_python("tools/dedup_control_gui.py"),
        ).grid(row=19, column=1, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self,
            text="Open Processing Logs",
            command=self.open_processing_logs,
        ).grid(row=19, column=2, sticky="ew", padx=5, pady=3)

        ttk.Checkbutton(
            self,
            text="Preview first when a standard Pillow job will create multiple images",
            variable=self.preview_standard_outputs,
        ).grid(row=20, column=0, columnspan=3, sticky="w", padx=5, pady=(3, 6))

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
