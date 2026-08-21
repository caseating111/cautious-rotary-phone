from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

try:
    from tools.custom_matrix_gui import CustomMatrixBuilder
    from tools.run_custom_matrix_job import run_job
except ModuleNotFoundError:
    from custom_matrix_gui import CustomMatrixBuilder
    from run_custom_matrix_job import run_job


class RecordedCustomMatrixBuilder(CustomMatrixBuilder):
    def build_matrix(self) -> None:
        try:
            selection = self.current_selection()
            self.status.set("Checking selected crops and building matrix…")
            self.update_idletasks()
            output = run_job(selection, no_open_output=False)
        except SystemExit as exc:
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
