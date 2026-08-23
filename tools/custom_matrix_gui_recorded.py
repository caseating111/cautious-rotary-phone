from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tools.custom_crop_inventory import inventory_summary, selected_inventory
    from tools.custom_matrix_gui import CustomMatrixBuilder
    from tools.custom_matrix_preview import build_preview as build_raw_preview, output_count
    from tools.output_processing_records import record_paths
    from tools.output_recipe_loader import default_recipe_folder, load_output_recipe
    from tools.run_custom_matrix_job import run_job as run_raw_job
    from tools.run_existing_pillow_from_config import open_output
except ModuleNotFoundError:
    from custom_crop_inventory import inventory_summary, selected_inventory
    from custom_matrix_gui import CustomMatrixBuilder
    from custom_matrix_preview import build_preview as build_raw_preview, output_count
    from output_processing_records import record_paths
    from output_recipe_loader import default_recipe_folder, load_output_recipe
    from run_custom_matrix_job import run_job as run_raw_job
    from run_existing_pillow_from_config import open_output


DISPLAY_MODES = ("Raw",)


class RecordedCustomMatrixBuilder(CustomMatrixBuilder):
    def __init__(self) -> None:
        super().__init__()
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=12, pady=(0, 6))
        self.display_mode = tk.StringVar(value="Raw")
        self.preview_first = tk.BooleanVar(value=True)
        ttk.Label(controls, text="Display mode").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.display_mode,
            values=DISPLAY_MODES,
            state="readonly",
            width=24,
        ).pack(side="left", padx=(6, 16))
        ttk.Button(controls, text="Open old recipe…", command=self.open_recipe).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Open Processing Logs", command=self.open_processing_logs).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(
            controls,
            text="Preview first when multiple outputs",
            variable=self.preview_first,
        ).pack(side="right")

    def open_processing_logs(self) -> None:
        folder = Path(self.config_data["matrix_output"]) / "Processing Logs"
        if not folder.is_dir():
            messagebox.showinfo(
                "Processing Logs",
                "No Processing Logs folder exists yet. It will be created after the first recorded custom output.",
            )
            return
        open_output(folder)

    def open_recipe(self) -> None:
        initial = default_recipe_folder(self.config_data["matrix_output"])
        chosen = filedialog.askopenfilename(
            title="Open custom matrix output recipe",
            initialdir=str(initial if initial.is_dir() else initial.parent),
            filetypes=[("JSON output recipes", "*.json"), ("All files", "*.*")],
        )
        if not chosen:
            return
        try:
            loaded = load_output_recipe(chosen)
            self.apply_selection(loaded["selection"])
            self.display_mode.set(loaded["display_mode"])
        except SystemExit as exc:
            messagebox.showerror("Open output recipe", str(exc))
            return
        old_output = loaded.get("output_path") or "unknown output"
        self.status.set(f"Restored recipe from {old_output}. Adjust it or rebuild as-is.")

    def check_availability(self) -> None:
        try:
            selection = self.current_selection()
            items = selected_inventory(self.config_data, selection)
        except SystemExit as exc:
            messagebox.showerror("Crop availability", str(exc))
            return
        summary = inventory_summary(items)
        current = sum(item.status == "current" for item in items)
        self.status.set(f"Selected crop availability: {current} / {len(items)} current.")
        messagebox.showinfo("Selected crop availability", summary)

    def build_matrix(self) -> None:
        preview = None
        try:
            selection = self.current_selection()
            if self.preview_first.get() and output_count(selection) > 1:
                self.status.set("Building one representative raw preview…")
                self.update_idletasks()
                preview = build_raw_preview(selection)
                open_output(preview.image)
                accepted = messagebox.askyesno(
                    "Custom matrix preview",
                    "One representative matrix has been opened.\n\n"
                    "Does this preview look suitable to use for the full selected output set?",
                )
                preview.cleanup()
                preview = None
                if not accepted:
                    self.status.set("Preview rejected. Full custom output was not generated.")
                    return

            self.status.set("Checking selected crops and building matrix…")
            self.update_idletasks()
            output = run_raw_job(selection, no_open_output=False)
        except SystemExit as exc:
            if preview is not None:
                preview.cleanup()
            messagebox.showerror("Custom matrix", str(exc))
            self.status.set("Custom matrix stopped; source CSVs and real crops were not changed.")
            return
        human_log, _machine_recipe = record_paths(Path(self.config_data["matrix_output"]), output)
        self.status.set(f"Created: {output} | processing log and recipe saved")
        messagebox.showinfo(
            "Custom matrix",
            f"Created focused matrix output:\n{output}\n\nProcessing Log:\n{human_log}\n\n"
            "The machine recipe was saved separately under _workflow.",
        )


def main() -> None:
    try:
        app = RecordedCustomMatrixBuilder()
    except SystemExit as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Custom matrix", str(exc))
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
