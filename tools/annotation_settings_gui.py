from __future__ import annotations

import copy
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from tkinter import colorchooser, messagebox, simpledialog, ttk
from typing import Any

from tools.applet_presets import (
    custom_colors,
    list_presets,
    load_preset,
    normalize_hex_color,
    save_custom_color,
    save_last,
    save_preset,
)
from tools.applets.annotation import HEADER_FIELDS, normalize_annotation_preset

COMMON_FONTS = (
    "Arial",
    "Arial Bold",
    "Tahoma",
    "Times New Roman",
    "Calibri",
    "Cambria",
    "Verdana",
)
FIELD_LABELS = {
    "date": "Date",
    "figure_description": "Figure description",
    "plate": "Plate",
    "condition": "Condition",
    "session": "Session",
    "media": "Media",
}


class AnnotationSettingsDialog(tk.Toplevel):
    """Edit independent styles for every header/in-image field and label set."""

    def __init__(
        self,
        parent: tk.Misc,
        initial: dict[str, Any],
        apply: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent)
        self.title("Annotation styles and presets")
        self.geometry("760x510")
        self.transient(parent)
        self.apply_callback = apply
        self.settings = normalize_annotation_preset(copy.deepcopy(initial))
        self.current_key = ""
        self.target = tk.StringVar(value="header:date")
        self.font = tk.StringVar()
        self.size = tk.StringVar()
        self.color = tk.StringVar()
        self.bold = tk.BooleanVar()
        self.visible = tk.BooleanVar(value=True)
        self.strain_colors = tk.StringVar()
        self.rotation = tk.StringVar()
        self.offset_x = tk.StringVar()
        self.offset_y = tk.StringVar()
        self.order = tk.StringVar()
        self.preset_name = tk.StringVar()
        self._build()
        self._load_target("header:date")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self) -> None:
        ttk.Label(
            self,
            text="Each label category is independent. Changes remain preview-only until the main applet accepts the derivative.",
            wraplength=720,
        ).pack(anchor="w", padx=10, pady=8)
        row = ttk.Frame(self)
        row.pack(fill="x", padx=10, pady=3)
        ttk.Label(row, text="Label set", width=15).pack(side="left")
        values = (
            [f"header:{field}" for field in HEADER_FIELDS]
            + [f"in_image:{field}" for field in HEADER_FIELDS]
            + ["strain", "vertical"]
        )
        target = ttk.Combobox(
            row, textvariable=self.target, values=values, state="readonly"
        )
        target.pack(side="left", fill="x", expand=True)
        target.bind("<<ComboboxSelected>>", self._switch)
        style = ttk.LabelFrame(self, text="Selected label-set style")
        style.pack(fill="x", padx=10, pady=6)
        for label, variable in (
            ("Font", self.font),
            ("Size", self.size),
            ("Colour (#RRGGBB)", self.color),
            ("Rotation ° clockwise", self.rotation),
            ("Offset X", self.offset_x),
            ("Offset Y", self.offset_y),
            ("Order", self.order),
        ):
            row = ttk.Frame(style)
            row.pack(fill="x", padx=6, pady=2)
            ttk.Label(row, text=label, width=22).pack(side="left")
            if label == "Font":
                ttk.Combobox(row, textvariable=variable, values=COMMON_FONTS).pack(
                    side="left", fill="x", expand=True
                )
                ttk.Button(row, text="Show all…", command=self.show_all_fonts).pack(
                    side="left", padx=(4, 0)
                )
            else:
                ttk.Entry(row, textvariable=variable).pack(
                    side="left", fill="x", expand=True
                )
                if label.startswith("Colour"):
                    ttk.Button(row, text="Choose…", command=self.choose_color).pack(
                        side="left", padx=(4, 0)
                    )
        flags = ttk.Frame(style)
        flags.pack(fill="x", padx=6, pady=3)
        ttk.Checkbutton(flags, text="Visible", variable=self.visible).pack(side="left")
        ttk.Checkbutton(flags, text="Bold", variable=self.bold).pack(
            side="left", padx=(12, 0)
        )
        row = ttk.Frame(style)
        row.pack(fill="x", padx=6, pady=2)
        ttk.Label(row, text="Per-strain colours", width=22).pack(side="left")
        ttk.Entry(row, textvariable=self.strain_colors).pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(
            style, text="Optional: WT=#0000FF; mutant=#FF0000", foreground="#555555"
        ).pack(anchor="w", padx=6)
        saved = custom_colors()
        if saved:
            ttk.Label(
                style, text="Saved colours: " + ", ".join(saved), wraplength=700
            ).pack(anchor="w", padx=6)
        preset = ttk.LabelFrame(self, text="Reusable annotation preset")
        preset.pack(fill="x", padx=10, pady=6)
        self.preset_box = ttk.Combobox(
            preset,
            textvariable=self.preset_name,
            state="readonly",
            values=list_presets("annotation"),
        )
        self.preset_box.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        ttk.Button(preset, text="Load", command=self.load_named).pack(side="left")
        ttk.Button(preset, text="Save as…", command=self.save_named).pack(
            side="left", padx=4
        )
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=8)
        ttk.Button(actions, text="Apply settings", command=self.apply).pack(
            side="right"
        )
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(
            side="right", padx=5
        )

    def _style_for(self, key: str) -> dict[str, Any]:
        if ":" in key:
            section, field = key.split(":", 1)
            return self.settings[f"{section}_field_styles"][field]
        return {
            "font_family": self.settings[f"{key}_font_family"],
            "font_size": self.settings[f"{key}_font_size"],
            "color": self.settings.get("text_color", "#000000"),
            "bold": self.settings[f"{key}_bold"],
            "rotation": self.settings[f"{key}_rotation_degrees"],
            "offset_x": self.settings.get(f"{key}_offset_x", 0),
            "offset_y": self.settings.get(f"{key}_offset_y", 0),
        }

    def _save_target(self) -> None:
        if not self.current_key:
            return
        try:
            style = {
                "font_family": self.font.get().strip() or "Arial",
                "font_size": int(self.size.get()),
                "color": normalize_hex_color(self.color.get()),
                "bold": self.bold.get(),
                "rotation": float(self.rotation.get()),
                "offset_x": float(self.offset_x.get()),
                "offset_y": float(self.offset_y.get()),
            }
            if style["font_size"] < 1:
                raise ValueError("Font size must be positive.")
            order = int(self.order.get()) if self.order.get().strip() else 1
        except ValueError as exc:
            raise ValueError(f"Invalid annotation style: {exc}") from exc
        if ":" in self.current_key:
            section, field = self.current_key.split(":", 1)
            self.settings[f"{section}_field_visibility"][field] = self.visible.get()
            self.settings[f"{section}_field_styles"][field] = style
            sequence = self.settings[f"{section}_order"]
            sequence.remove(field)
            sequence.insert(max(0, min(order - 1, len(sequence))), field)
        else:
            key = self.current_key
            self.settings[f"{key}_visible"] = self.visible.get()
            for field, value in style.items():
                if field == "font_family":
                    self.settings[f"{key}_font_family"] = value
                elif field == "font_size":
                    self.settings[f"{key}_font_size"] = value
                elif field == "bold":
                    self.settings[f"{key}_bold"] = value
                elif field == "rotation":
                    self.settings[f"{key}_rotation_degrees"] = value
                elif field in {"offset_x", "offset_y"}:
                    self.settings[f"{key}_{field}"] = value
            self.settings["text_color"] = style["color"]
        mappings = {}
        for item in self.strain_colors.get().split(";"):
            if not item.strip():
                continue
            if "=" not in item:
                raise ValueError("Per-strain colours must use Label=#RRGGBB entries.")
            label, value = item.split("=", 1)
            mappings[label.strip()] = normalize_hex_color(value)
        self.settings["strain_label_colors"] = mappings

    def _load_target(self, key: str) -> None:
        style = self._style_for(key)
        self.current_key = key
        self.font.set(str(style.get("font_family", "Arial")))
        self.size.set(str(style.get("font_size", 18)))
        color = style.get("color", "#000000")
        if isinstance(color, (list, tuple)):
            color = "#" + "".join(f"{int(value):02X}" for value in color)
        self.color.set(str(color))
        self.bold.set(bool(style.get("bold", False)))
        if ":" in key:
            section, field = key.split(":", 1)
            self.visible.set(
                self.settings[f"{section}_field_visibility"].get(field, True)
            )
        else:
            self.visible.set(self.settings.get(f"{key}_visible", True))
        self.strain_colors.set(
            "; ".join(
                f"{label}={color}"
                for label, color in self.settings.get("strain_label_colors", {}).items()
            )
        )
        self.rotation.set(str(style.get("rotation", 0)))
        self.offset_x.set(str(style.get("offset_x", 0)))
        self.offset_y.set(str(style.get("offset_y", 0)))
        if ":" in key:
            section, field = key.split(":", 1)
            self.order.set(str(self.settings[f"{section}_order"].index(field) + 1))
        else:
            self.order.set("")

    def _switch(self, _event=None) -> None:
        try:
            self._save_target()
        except ValueError as exc:
            messagebox.showerror("Annotation style", str(exc))
            self.target.set(self.current_key)
            return
        self._load_target(self.target.get())

    def choose_color(self) -> None:
        chosen = colorchooser.askcolor(color=self.color.get(), parent=self)[1]
        if chosen:
            self.color.set(chosen.upper())
            save_custom_color(chosen)

    def show_all_fonts(self) -> None:
        browser = tk.Toplevel(self)
        browser.title("All system fonts")
        browser.geometry("420x500")
        search = tk.StringVar()
        ttk.Entry(browser, textvariable=search).pack(fill="x", padx=6, pady=6)
        box = tk.Listbox(browser)
        box.pack(fill="both", expand=True, padx=6)
        families = sorted(set(tkfont.families(self)), key=str.casefold)

        def refresh(*_args):
            query = search.get().casefold()
            box.delete(0, "end")
            for family in families:
                if query in family.casefold():
                    box.insert("end", family)

        def select(_event=None):
            if box.curselection():
                self.font.set(box.get(box.curselection()[0]))
                browser.destroy()

        search.trace_add("write", refresh)
        box.bind("<Double-Button-1>", select)
        ttk.Button(browser, text="Use selected", command=select).pack(pady=5)
        refresh()

    def save_named(self) -> None:
        try:
            self._save_target()
        except ValueError as exc:
            messagebox.showerror("Annotation preset", str(exc))
            return
        name = simpledialog.askstring("Annotation preset", "Preset name:", parent=self)
        if name:
            save_preset("annotation", name, self.settings)
            self.preset_box.configure(values=list_presets("annotation"))
            self.preset_name.set(name)

    def load_named(self) -> None:
        if self.preset_name.get():
            self.settings = normalize_annotation_preset(
                load_preset("annotation", self.preset_name.get())
            )
            self._load_target(self.target.get())

    def apply(self) -> None:
        try:
            self._save_target()
        except ValueError as exc:
            messagebox.showerror("Annotation settings", str(exc))
            return
        save_last("annotation", self.settings)
        self.apply_callback(copy.deepcopy(self.settings))
        self.destroy()
