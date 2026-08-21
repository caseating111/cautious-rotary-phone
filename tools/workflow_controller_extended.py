from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools import standard_pillow_preview
    from tools.workflow_controller import Controller, PILLOW_JOBS
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter
    import standard_pillow_preview
    from workflow_controller import Controller, PILLOW_JOBS


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
        ttk.Label(
            self,
            text="Focused Pillow composition tools use existing validated crops and do not alter source CSVs/crops.",
            wraplength=250,
        ).grid(row=19, column=2, sticky="w", padx=5, pady=3)

        ttk.Checkbutton(
            self,
            text="Preview first when a standard Pillow job will create multiple images",
            variable=self.preview_standard_outputs,
        ).grid(row=20, column=0, columnspan=3, sticky="w", padx=5, pady=(3, 6))

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

    def run_pillow_job(self) -> None:
        if not self.preview_standard_outputs.get():
            super().run_pillow_job()
            return

        if not self.save():
            return
        alias = PILLOW_JOBS[self.pillow_job.get()]
        preview = None
        try:
            config = pillow_adapter.load_config()
            count = self.standard_output_count(alias, config)
            if count <= 1:
                super().run_pillow_job()
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
        super().run_pillow_job()


def main() -> None:
    app = ExtendedController()
    app.mainloop()


if __name__ == "__main__":
    main()
