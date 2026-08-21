from __future__ import annotations

import json
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter


class CustomMatrixBuilder(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Custom matrix comparison")
        self.geometry("760x720")
        self.minsize(640, 520)
        self.config_data = pillow_adapter.load_config()
        pillow_adapter.validate_csvs(self.config_data)
        self.group_vars: dict[tuple[str, str], list[tuple[int, str, tk.BooleanVar]]] = {}
        self.condition_vars: dict[str, tk.BooleanVar] = {}
        self.state_vars = {state: tk.BooleanVar(value=True) for state in ("Top", "Low")}
        self.status = tk.StringVar(value="Choose any subset. Source CSVs and real crops are never changed.")
        self.build_ui()
        self.load_initial_selection()

    def project_data(self) -> tuple[dict[tuple[str, str], list[tuple[int, str]]], list[str]]:
        _, grid_rows = custom.read_rows(Path(self.config_data["grid_csv"]))
        _, condition_rows = custom.read_rows(Path(self.config_data["condition_order_csv"]))
        groups: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
        for row in grid_rows:
            key = ((row.get("Experiment") or "").strip(), (row.get("Set") or "").strip())
            groups[key].append((int((row.get("Column") or "0").strip()), (row.get("Strain") or "").strip()))
        for key in groups:
            groups[key].sort()
        conditions = [
            (row.get("Type") or "").strip()
            for row in sorted(condition_rows, key=lambda row: int((row.get("Order") or "0").strip()))
        ]
        return dict(groups), conditions

    def build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text="All", command=lambda: self.set_all(True)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="None", command=lambda: self.set_all(False)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Restore last selection", command=self.restore_last_selection).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Check crop availability", command=self.check_availability).pack(side="right", padx=2)

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=8)
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)
        self.body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        groups, conditions = self.project_data()
        for exp_set, rows in groups.items():
            exp, set_name = exp_set
            frame = ttk.LabelFrame(self.body, text=f"{exp} / {set_name}")
            frame.pack(fill="x", padx=4, pady=5)
            controls = ttk.Frame(frame)
            controls.pack(fill="x")
            ttk.Button(controls, text="All", width=6, command=lambda key=exp_set: self.set_group(key, True)).pack(side="left", padx=2, pady=2)
            ttk.Button(controls, text="None", width=6, command=lambda key=exp_set: self.set_group(key, False)).pack(side="left", padx=2, pady=2)
            ttk.Button(
                controls,
                text="Only this set",
                command=lambda key=exp_set: self.select_only_group(key),
            ).pack(side="left", padx=(8, 2), pady=2)
            vars_for_group = []
            cells = ttk.Frame(frame)
            cells.pack(fill="x", padx=4, pady=3)
            for index, (column, strain) in enumerate(rows):
                var = tk.BooleanVar(value=True)
                vars_for_group.append((column, strain, var))
                label = f"{column}: {strain}"
                ttk.Checkbutton(cells, text=label, variable=var).grid(row=index // 4, column=index % 4, sticky="w", padx=4, pady=2)
            self.group_vars[exp_set] = vars_for_group

        condition_frame = ttk.LabelFrame(self.body, text="Conditions / types")
        condition_frame.pack(fill="x", padx=4, pady=5)
        condition_controls = ttk.Frame(condition_frame)
        condition_controls.pack(fill="x", padx=2, pady=(2, 0))
        ttk.Button(condition_controls, text="All", width=6, command=lambda: self.set_conditions(True)).pack(side="left", padx=2)
        ttk.Button(condition_controls, text="None", width=6, command=lambda: self.set_conditions(False)).pack(side="left", padx=2)
        condition_cells = ttk.Frame(condition_frame)
        condition_cells.pack(fill="x", padx=2, pady=2)
        for index, condition in enumerate(conditions):
            var = tk.BooleanVar(value=True)
            self.condition_vars[condition] = var
            ttk.Checkbutton(condition_cells, text=condition, variable=var).grid(row=index // 5, column=index % 5, sticky="w", padx=6, pady=3)

        state_frame = ttk.LabelFrame(self.body, text="Crop state")
        state_frame.pack(fill="x", padx=4, pady=5)
        for state, var in self.state_vars.items():
            ttk.Checkbutton(state_frame, text=state, variable=var).pack(side="left", padx=8, pady=4)

        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=8, pady=8)
        ttk.Label(footer, textvariable=self.status, wraplength=540).pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Build custom matrix", command=self.build_matrix).pack(side="right", padx=4)

    def set_group(self, key: tuple[str, str], value: bool) -> None:
        for _column, _strain, var in self.group_vars[key]:
            var.set(value)

    def select_only_group(self, key: tuple[str, str]) -> None:
        for group_key in self.group_vars:
            self.set_group(group_key, group_key == key)
        exp, set_name = key
        self.status.set(f"Selected only {exp} / {set_name}; conditions and Top/Low were left unchanged.")

    def set_conditions(self, value: bool) -> None:
        for var in self.condition_vars.values():
            var.set(value)

    def set_all(self, value: bool) -> None:
        for key in self.group_vars:
            self.set_group(key, value)
        self.set_conditions(value)
        for var in self.state_vars.values():
            var.set(value)

    def current_selection(self) -> dict:
        groups = []
        for (exp, set_name), entries in self.group_vars.items():
            columns = [column for column, _strain, var in entries if var.get()]
            if columns:
                groups.append({"experiment": exp, "set": set_name, "columns": columns})
        conditions = [name for name, var in self.condition_vars.items() if var.get()]
        states = [name for name, var in self.state_vars.items() if var.get()]
        return custom.normalize_selection({"groups": groups, "conditions": conditions, "states": states})

    def apply_selection(self, selection: dict) -> None:
        selection = custom.normalize_selection(selection)
        self.set_all(False)
        wanted_groups = {
            (group["experiment"].casefold(), group["set"].casefold()): set(group["columns"])
            for group in selection["groups"]
        }
        for (exp, set_name), entries in self.group_vars.items():
            wanted = wanted_groups.get((exp.casefold(), set_name.casefold()), set())
            for column, _strain, var in entries:
                var.set(column in wanted)
        wanted_conditions = {value.casefold() for value in selection["conditions"]}
        for condition, var in self.condition_vars.items():
            var.set(condition.casefold() in wanted_conditions)
        wanted_states = set(selection["states"])
        for state, var in self.state_vars.items():
            var.set(state in wanted_states)

    def load_initial_selection(self) -> None:
        if custom.LAST_SELECTION_FILE.is_file():
            try:
                self.apply_selection(json.loads(custom.LAST_SELECTION_FILE.read_text(encoding="utf-8")))
                self.status.set("Restored the last custom selection. Use All to return to the full project.")
                return
            except (OSError, json.JSONDecodeError, SystemExit):
                pass
        self.status.set("Full project selected. Narrow only what you want to compare.")

    def restore_last_selection(self) -> None:
        if not custom.LAST_SELECTION_FILE.is_file():
            messagebox.showinfo("Custom matrix", "No previous custom selection has been saved yet.")
            return
        try:
            self.apply_selection(json.loads(custom.LAST_SELECTION_FILE.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, SystemExit) as exc:
            messagebox.showerror("Custom matrix", f"Could not restore the previous selection:\n{exc}")
            return
        self.status.set("Previous custom selection restored.")

    def check_availability(self) -> None:
        try:
            selection = self.current_selection()
            with tempfile_selection_csvs(self.config_data, selection) as filtered:
                contract = pillow_adapter.expected_crop_contract(filtered["grid_csv"], filtered["images_csv"])
                selected = pillow_adapter.validate_unique_crop_matches(
                    Path(self.config_data["crop_output"]), filtered["grid_csv"], filtered["images_csv"], allow_missing=True
                )
            total = len(contract)
            self.status.set(f"Exact current crops available: {len(selected)} / {total}. Build remains strict and will stop if selected crops are missing.")
        except SystemExit as exc:
            messagebox.showerror("Crop availability", str(exc))

    def build_matrix(self) -> None:
        try:
            selection = self.current_selection()
            self.status.set("Building selected matrix from existing crops…")
            self.update_idletasks()
            output = custom.run_selection(selection, no_open_output=False)
        except SystemExit as exc:
            messagebox.showerror("Custom matrix", str(exc))
            self.status.set("Custom matrix stopped; no source CSVs or real crops were changed.")
            return
        self.status.set(f"Created: {output}")
        messagebox.showinfo("Custom matrix", f"Created focused matrix output:\n{output}")


class tempfile_selection_csvs:
    def __init__(self, config: dict, selection: dict) -> None:
        import tempfile

        self.config = config
        self.selection = selection
        self.temp = tempfile.TemporaryDirectory(prefix="matrix-availability-", dir=custom.APP_DIR)
        self.root = Path(self.temp.name)

    def __enter__(self) -> dict[str, Path]:
        return custom.filter_project_csvs(self.config, self.selection, self.root)

    def __exit__(self, exc_type, exc, tb) -> None:
        self.temp.cleanup()


def main() -> None:
    try:
        app = CustomMatrixBuilder()
    except SystemExit as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Custom matrix", str(exc))
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
