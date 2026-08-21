from __future__ import annotations

import tkinter as tk
from tkinter import ttk

try:
    from tools.workflow_controller import Controller
except ModuleNotFoundError:
    from workflow_controller import Controller


class ExtendedController(Controller):
    def __init__(self) -> None:
        super().__init__()
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


def main() -> None:
    app = ExtendedController()
    app.mainloop()


if __name__ == "__main__":
    main()
