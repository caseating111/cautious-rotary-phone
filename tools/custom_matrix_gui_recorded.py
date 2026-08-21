from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

try:
    from tools.custom_matrix_gui import CustomMatrixBuilder
    from tools.custom_matrix_preview import build_preview, output_count
    from tools.run_custom_matrix_job import run_job
    from tools.run_existing_pillow_from_config import open_output
except ModuleNotFoundError:
    from custom_matrix_gui import CustomMatrixBuilder
    from custom_matrix_preview import build_preview, output_count
    from run_custom_matrix_job import run_job
    from run_existing_pillow_from_config import open_output


class RecordedCustomMatrixBuilder(CustomMatrixBuilder):
    def __init__(self) -> None:
        super().__init__()
        self.preview_first = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self,
            text="Preview first when multiple outputs",
            variable=self.preview_first,
        ).pack(anchor="e", padx=12, pady=(0, 6))

    def build_matrix(self) -> None:
        preview = None
        try:
            selection = self.current_selection()
            if self.preview_first.get() and output_count(selection) > 1:
                self.status.set("Building one representative preview…")
                self.update_idletasks()
                preview = build_preview(selection)
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
            output = run_job(selection, no_open_output=False)
        except SystemExit as exc:
            if preview is not None:
                preview.cleanup()
            messagebox.showerror("Custom matrix", str(exc))
            self.status.set("Custom matrix stopped; source CSVs and real crops were not changed.")
            return
        self.status.set(f"Created: {output} | processing log and recipe saved")
        messagebox.showinfo(
            "Custom matrix",
            f"Created focused matrix output:\n{output}\n\nA readable Processing Log and machine output recipe were also saved.",
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
