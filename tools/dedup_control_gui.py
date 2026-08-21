from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.run_dedup_with_control import control_groups, run
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter
    from run_dedup_with_control import control_groups, run


class DedupControlGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Preferred WT control source")
        self.resizable(False, False)
        self.config_data = pillow_adapter.load_config()
        pillow_adapter.validate_csvs(self.config_data)
        groups = control_groups(Path(self.config_data["grid_csv"]))
        if not groups:
            raise SystemExit("No WT X/WT Y control rows were found in grid.csv.")
        self.groups = groups
        labels = [self.group_label(key) for key in sorted(groups)]
        preferred = "E2 / A"
        self.choice = tk.StringVar(value=preferred if preferred in labels else labels[0])
        self.status = tk.StringVar(value="Choose the experiment/set whose WT culture should be preferred.")

        pad = {"padx": 8, "pady": 6}
        ttk.Label(self, text="Preferred WT source").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.choice, values=labels, state="readonly", width=28).grid(row=0, column=1, **pad)
        ttk.Label(
            self,
            text="The existing deduplicated all-strains script still falls back to the first available candidate if the chosen group lacks one recognised WT control.",
            wraplength=480,
        ).grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, textvariable=self.status, wraplength=480).grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        ttk.Button(self, text="Build deduplicated all-strains output", command=self.build).grid(row=3, column=0, columnspan=2, sticky="ew", **pad)

    def group_label(self, key: tuple[str, str]) -> str:
        return f"{key[0]} / {key[1]}"

    def selected_key(self) -> tuple[str, str]:
        label = self.choice.get()
        for key in self.groups:
            if self.group_label(key) == label:
                return key
        raise SystemExit(f"Unknown preferred control selection: {label}")

    def build(self) -> None:
        try:
            exp, set_name = self.selected_key()
            controls = ", ".join(sorted(self.groups[(exp, set_name)]))
            self.status.set(f"Building with preferred source {exp}/{set_name} ({controls})…")
            self.update_idletasks()
            output = run(exp, set_name, no_open_output=False)
        except SystemExit as exc:
            messagebox.showerror("Preferred WT source", str(exc))
            self.status.set("Output stopped without modifying source crops.")
            return
        self.status.set(f"Created: {output}")
        messagebox.showinfo("Preferred WT source", f"Created output:\n{output}")


def main() -> None:
    try:
        app = DedupControlGui()
    except SystemExit as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Preferred WT source", str(exc))
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
