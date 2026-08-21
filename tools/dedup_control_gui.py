from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.output_processing_records import record_paths
    from tools.run_dedup_with_control import build_preview, control_groups, load_preferred_source, run
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter
    from output_processing_records import record_paths
    from run_dedup_with_control import build_preview, control_groups, load_preferred_source, run


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
        ordered_keys = sorted(groups)
        labels = [self.group_label(key) for key in ordered_keys]
        remembered = load_preferred_source()
        initial_key = remembered if remembered in groups else ordered_keys[0]
        self.choice = tk.StringVar(value=self.group_label(initial_key))
        self.preview_first = tk.BooleanVar(value=True)
        if remembered in groups:
            status = f"Restored last successful WT source: {remembered[0]}/{remembered[1]}."
        else:
            status = "Choose the experiment/set whose WT culture should be preferred."
        self.status = tk.StringVar(value=status)

        pad = {"padx": 8, "pady": 6}
        ttk.Label(self, text="Preferred WT source").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(self, textvariable=self.choice, values=labels, state="readonly", width=28).grid(row=0, column=1, **pad)
        ttk.Label(
            self,
            text="The existing deduplicated all-strains script still falls back to the first available candidate if the chosen group lacks one recognised WT control.",
            wraplength=480,
        ).grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(
            self,
            text="Preview Top output before generating Top + Low",
            variable=self.preview_first,
        ).grid(row=2, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, textvariable=self.status, wraplength=480).grid(row=3, column=0, columnspan=2, sticky="w", **pad)
        ttk.Button(self, text="Build deduplicated all-strains output", command=self.build).grid(row=4, column=0, columnspan=2, sticky="ew", **pad)

    def group_label(self, key: tuple[str, str]) -> str:
        return f"{key[0]} / {key[1]}"

    def selected_key(self) -> tuple[str, str]:
        label = self.choice.get()
        for key in self.groups:
            if self.group_label(key) == label:
                return key
        raise SystemExit(f"Unknown preferred control selection: {label}")

    def build(self) -> None:
        preview = None
        try:
            exp, set_name = self.selected_key()
            controls = ", ".join(sorted(self.groups[(exp, set_name)]))
            if self.preview_first.get():
                self.status.set(f"Building representative Top preview with preferred source {exp}/{set_name}…")
                self.update_idletasks()
                preview = build_preview(exp, set_name)
                pillow_adapter.open_output(preview.image)
                accepted = messagebox.askyesno(
                    "Preferred WT preview",
                    f"One Top preview has been opened using preferred WT source {exp}/{set_name}.\n\n"
                    "Generate the full Top + Low output now?",
                )
                preview.cleanup()
                preview = None
                if not accepted:
                    self.status.set("Preview rejected. Full deduplicated output was not generated.")
                    return

            self.status.set(f"Building with preferred source {exp}/{set_name} ({controls})…")
            self.update_idletasks()
            output = run(exp, set_name, no_open_output=False)
        except SystemExit as exc:
            if preview is not None:
                preview.cleanup()
            messagebox.showerror("Preferred WT source", str(exc))
            self.status.set("Output stopped without modifying source crops.")
            return
        human_log, _machine_recipe = record_paths(Path(self.config_data["matrix_output"]), output)
        self.status.set(f"Created: {output} | WT source remembered | processing log saved")
        messagebox.showinfo(
            "Preferred WT source",
            f"Created output:\n{output}\n\nProcessing Log:\n{human_log}\n\n"
            "The machine recipe was saved separately under _workflow.",
        )


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
