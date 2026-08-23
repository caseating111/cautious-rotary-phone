from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tools import unified_matrix_export as unified
    from tools.custom_crop_inventory import inventory_summary, selected_inventory
    from tools.custom_matrix_gui import CustomMatrixBuilder
    from tools.custom_matrix_preview import build_preview as build_raw_preview, output_count
    from tools.output_recipe_loader import default_recipe_folder, load_output_recipe
    from tools.run_existing_pillow_from_config import open_output
except ModuleNotFoundError:
    import unified_matrix_export as unified
    from custom_crop_inventory import inventory_summary, selected_inventory
    from custom_matrix_gui import CustomMatrixBuilder
    from custom_matrix_preview import build_preview as build_raw_preview, output_count
    from output_recipe_loader import default_recipe_folder, load_output_recipe
    from run_existing_pillow_from_config import open_output


class RecordedCustomMatrixBuilder(CustomMatrixBuilder):
    def initialize_extension_state(self) -> None:
        default_alias = "per-experiment" if "per-experiment" in unified.OUTPUT_TYPES else next(iter(unified.OUTPUT_TYPES))
        self.output_vars = {
            alias: tk.BooleanVar(value=alias == default_alias)
            for alias in unified.OUTPUT_TYPES
        }
        self.normalize_wt_names = tk.BooleanVar(value=True)
        self.preferred_wt = tk.StringVar()
        self.preset_name = tk.StringVar()
        self.preview_first = tk.BooleanVar(value=False)
        self.control_key_by_label: dict[str, tuple[str, str]] = {}
        self.preset_box: ttk.Combobox | None = None
        self.preferred_wt_box: ttk.Combobox | None = None

    def build_top_controls(self) -> None:
        frame = ttk.LabelFrame(self, text="Dataset presets")
        frame.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(frame, text="Preset name").pack(side="left", padx=(6, 4), pady=5)
        self.preset_box = ttk.Combobox(frame, textvariable=self.preset_name, width=28)
        self.preset_box.pack(side="left", padx=(0, 5), pady=5)
        ttk.Button(frame, text="Save / replace", command=self.save_named_preset).pack(side="left", padx=2)
        ttk.Button(frame, text="Load", command=self.load_named_preset).pack(side="left", padx=2)
        ttk.Button(frame, text="Delete", command=self.delete_named_preset).pack(side="left", padx=2)
        ttk.Button(frame, text="Open old recipe...", command=self.open_recipe).pack(side="right", padx=(2, 6))
        ttk.Button(frame, text="Open Processing Logs", command=self.open_processing_logs).pack(side="right", padx=2)
        self.refresh_presets()

    def build_selection_options(self) -> None:
        output_frame = ttk.LabelFrame(self.body, text="Outputs to build in this run")
        output_frame.pack(fill="x", padx=4, pady=5)
        for index, (alias, label) in enumerate(unified.OUTPUT_TYPES.items()):
            ttk.Checkbutton(
                output_frame,
                text=label,
                variable=self.output_vars[alias],
                command=self.output_selection_changed,
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=8, pady=3)

        wt_frame = ttk.LabelFrame(self.body, text="Duplicate-WT handling")
        wt_frame.pack(fill="x", padx=4, pady=5)
        ttk.Checkbutton(
            wt_frame,
            text="Normalize WT separators (WT-X, WT_X and WT X are equivalent)",
            variable=self.normalize_wt_names,
            command=self.output_selection_changed,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 2))
        ttk.Label(wt_frame, text="Preferred WT source").grid(row=1, column=0, sticky="w", padx=8, pady=(2, 5))
        self.preferred_wt_box = ttk.Combobox(
            wt_frame,
            textvariable=self.preferred_wt,
            state="disabled",
            width=34,
        )
        self.preferred_wt_box.grid(row=1, column=1, sticky="w", padx=8, pady=(2, 5))

        preview_frame = ttk.Frame(self.body)
        preview_frame.pack(fill="x", padx=4, pady=3)
        ttk.Checkbutton(
            preview_frame,
            text="Preview one selected per-experiment matrix first",
            variable=self.preview_first,
        ).pack(side="left", padx=4)
        self.refresh_control_sources()

    def build_action_button(self, parent: ttk.Frame) -> None:
        ttk.Button(parent, text="Build selected outputs", command=self.build_matrix).pack(side="right", padx=4)

    def on_selection_changed(self) -> None:
        if self.preferred_wt_box is not None:
            self.refresh_control_sources()

    def output_selection_changed(self) -> None:
        self.refresh_control_sources()

    def selected_outputs(self) -> list[str]:
        return [alias for alias, var in self.output_vars.items() if var.get()]

    def refresh_control_sources(self) -> None:
        if self.preferred_wt_box is None:
            return
        dedup_selected = "all-strains-dedup" in self.selected_outputs()
        groups: object = []
        try:
            selection = self.current_selection()
            groups = unified.control_groups_for_selection(
                self.config_data,
                selection,
                normalize_wt_names=self.normalize_wt_names.get(),
            )
        except SystemExit:
            groups = []

        iterable = groups.keys() if isinstance(groups, dict) else groups
        keys = [(str(item[0]), str(item[1])) for item in iterable]
        self.control_key_by_label = {f"{exp} / {set_name}": (exp, set_name) for exp, set_name in keys}
        labels = list(self.control_key_by_label)
        self.preferred_wt_box.configure(values=labels)
        current = self.preferred_wt.get()
        if current not in self.control_key_by_label:
            self.preferred_wt.set(labels[0] if labels else "")
        self.preferred_wt_box.configure(state="readonly" if dedup_selected and labels else "disabled")

    def current_request(self) -> dict:
        selection = self.current_selection()
        preferred = self.control_key_by_label.get(self.preferred_wt.get())
        request = {
            "selection": selection,
            "outputs": self.selected_outputs(),
            "preferred_wt": (
                {"experiment": preferred[0], "set": preferred[1]}
                if preferred is not None
                else None
            ),
            "normalize_wt_names": self.normalize_wt_names.get(),
        }
        return unified.normalize_request(request)

    def apply_request(self, request: dict) -> None:
        clean = unified.normalize_request(request)
        self.apply_selection(clean["selection"])
        wanted = set(clean["outputs"])
        for alias, var in self.output_vars.items():
            var.set(alias in wanted)
        self.normalize_wt_names.set(bool(clean.get("normalize_wt_names", True)))
        self.refresh_control_sources()
        preferred = clean.get("preferred_wt")
        if isinstance(preferred, dict):
            wanted_key = (str(preferred.get("experiment", "")), str(preferred.get("set", "")))
            for label, key in self.control_key_by_label.items():
                if (key[0].casefold(), key[1].casefold()) == (
                    wanted_key[0].casefold(),
                    wanted_key[1].casefold(),
                ):
                    self.preferred_wt.set(label)
                    break

    def refresh_presets(self) -> None:
        try:
            names = unified.preset_names(self.config_data)
        except (OSError, SystemExit) as exc:
            names = []
            self.status.set(f"Could not list dataset presets: {exc}")
        if self.preset_box is not None:
            self.preset_box.configure(values=names)

    def save_named_preset(self) -> None:
        name = self.preset_name.get().strip()
        try:
            request = self.current_request()
            unified.save_preset(self.config_data, name, request)
        except (OSError, SystemExit) as exc:
            messagebox.showerror("Matrix preset", str(exc))
            return
        self.refresh_presets()
        self.preset_name.set(name)
        self.status.set(f"Saved dataset preset: {name}")

    def load_named_preset(self) -> None:
        name = self.preset_name.get().strip()
        try:
            request = unified.load_preset(self.config_data, name)
            self.apply_request(request)
        except (OSError, SystemExit) as exc:
            messagebox.showerror("Matrix preset", str(exc))
            return
        self.status.set(f"Loaded dataset preset: {name}")

    def delete_named_preset(self) -> None:
        name = self.preset_name.get().strip()
        if not name:
            messagebox.showerror("Matrix preset", "Choose or enter a preset name first.")
            return
        if not messagebox.askyesno("Delete matrix preset", f"Delete dataset preset {name!r}?"):
            return
        try:
            unified.delete_preset(self.config_data, name)
        except (OSError, SystemExit) as exc:
            messagebox.showerror("Matrix preset", str(exc))
            return
        self.preset_name.set("")
        self.refresh_presets()
        self.status.set(f"Deleted dataset preset: {name}")

    def open_processing_logs(self) -> None:
        folder = Path(self.config_data["matrix_output"]) / "Processing Logs"
        if not folder.is_dir():
            messagebox.showinfo(
                "Processing Logs",
                "No Processing Logs folder exists yet. It will be created after the first recorded output run.",
            )
            return
        open_output(folder)

    def open_recipe(self) -> None:
        initial = default_recipe_folder(self.config_data["matrix_output"])
        chosen = filedialog.askopenfilename(
            title="Open previous custom-matrix output recipe",
            initialdir=str(initial if initial.is_dir() else initial.parent),
            filetypes=[("JSON output recipes", "*.json"), ("All files", "*.*")],
        )
        if not chosen:
            return
        try:
            loaded = load_output_recipe(chosen)
            self.apply_selection(loaded["selection"])
            for alias, var in self.output_vars.items():
                var.set(alias == "per-experiment")
            self.refresh_control_sources()
        except SystemExit as exc:
            messagebox.showerror("Open output recipe", str(exc))
            return
        old_output = loaded.get("output_path") or "unknown output"
        self.status.set(f"Restored legacy per-experiment recipe from {old_output}. Adjust it or rebuild as-is.")

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
            request = self.current_request()
            selection = request["selection"]
            if (
                self.preview_first.get()
                and "per-experiment" in request["outputs"]
                and output_count(selection) > 1
            ):
                self.status.set("Building one representative per-experiment preview...")
                self.update_idletasks()
                preview = build_raw_preview(selection)
                open_output(preview.image)
                accepted = messagebox.askyesno(
                    "Matrix preview",
                    "One representative per-experiment matrix has been opened.\n\n"
                    "Continue with every checked output type?",
                )
                preview.cleanup()
                preview = None
                if not accepted:
                    self.status.set("Preview rejected. No selected outputs were published.")
                    return

            self.status.set("Checking selected crops and building every checked output...")
            self.update_idletasks()
            result = unified.run_job(request, no_open_output=False)
        except (OSError, SystemExit) as exc:
            if preview is not None:
                preview.cleanup()
            messagebox.showerror("Build selected outputs", str(exc))
            self.status.set("Output run stopped; source CSVs and real crops were not changed.")
            return

        run_id = result["run_id"]
        published = result["published_paths"]
        log = result["log"]
        recipe = result["recipe"]
        self.refresh_presets()
        self.status.set(f"{run_id}: published {len(published)} file(s) | Processing Log: {log}")
        messagebox.showinfo(
            "Build selected outputs",
            f"{run_id} published {len(published)} file(s).\n\n"
            f"Processing Log:\n{log}\n\n"
            f"Machine recipe:\n{recipe}",
        )


def main() -> None:
    try:
        app = RecordedCustomMatrixBuilder()
    except SystemExit as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Build matrices and labelled crops", str(exc))
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
