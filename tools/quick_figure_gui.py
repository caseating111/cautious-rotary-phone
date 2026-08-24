from __future__ import annotations

import csv
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from PIL import Image, ImageTk

from tools.applet_presets import (
    list_presets,
    load_last,
    load_preset,
    save_last,
    save_preset,
)
from tools.applets.quick_figure import (
    align_image_to_edge,
    annotate_quick,
    calculate_box_from_roi,
    export_wells,
    load_quick_csv,
    orient_image,
    register_quick_grid,
    save_quick_grid,
    set_grid_qc,
)


class QuickImageCanvas(ttk.Frame):
    """Small fit-to-window viewer used only by a detached Quick Figures window."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self, background="#242424", highlightthickness=0, cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)
        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.offset = (0.0, 0.0)
        self.click_handler: Callable[[tuple[float, float]], None] | None = None
        self.drag_handler: (
            Callable[[tuple[float, float], tuple[float, float]], None] | None
        ) = None
        self.drag_start: tuple[float, float] | None = None
        self.canvas.bind("<Configure>", lambda _event: self._render())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def show(self, image: Image.Image) -> None:
        self.image = image.copy()
        self._render()

    def set_handlers(self, *, click=None, drag=None) -> None:
        self.click_handler = click
        self.drag_handler = drag
        self.drag_start = None

    def draw_points(self, points: list[tuple[float, float]]) -> None:
        self.canvas.delete("overlay")
        for index, (x, y) in enumerate(points, 1):
            cx, cy = self.offset[0] + x * self.scale, self.offset[1] + y * self.scale
            self.canvas.create_oval(
                cx - 5,
                cy - 5,
                cx + 5,
                cy + 5,
                outline="#00ffff",
                width=2,
                tags="overlay",
            )
            self.canvas.create_text(
                cx + 8, cy - 8, text=str(index), fill="#00ffff", tags="overlay"
            )

    def draw_box(self, box: dict[str, Any]) -> None:
        self.canvas.delete("overlay")
        self.canvas.create_rectangle(
            self.offset[0] + box["left"] * self.scale,
            self.offset[1] + box["top"] * self.scale,
            self.offset[0] + box["right"] * self.scale,
            self.offset[1] + box["bottom"] * self.scale,
            outline="#00ffff",
            width=3,
            tags="overlay",
        )

    def _render(self) -> None:
        self.canvas.delete("all")
        if self.image is None:
            self.canvas.create_text(300, 220, text="Choose an image", fill="#dddddd")
            return
        width, height = (
            max(self.canvas.winfo_width(), 100),
            max(self.canvas.winfo_height(), 100),
        )
        self.scale = min(width / self.image.width, height / self.image.height)
        shown = self.image.resize(
            (
                max(1, round(self.image.width * self.scale)),
                max(1, round(self.image.height * self.scale)),
            ),
            Image.Resampling.LANCZOS,
        )
        self.photo = ImageTk.PhotoImage(shown)
        self.offset = ((width - shown.width) / 2, (height - shown.height) / 2)
        self.canvas.create_image(*self.offset, image=self.photo, anchor="nw")

    def _point(self, event: tk.Event) -> tuple[float, float] | None:
        if self.image is None:
            return None
        point = (
            (event.x - self.offset[0]) / self.scale,
            (event.y - self.offset[1]) / self.scale,
        )
        return (
            point
            if 0 <= point[0] < self.image.width and 0 <= point[1] < self.image.height
            else None
        )

    def _press(self, event: tk.Event) -> None:
        point = self._point(event)
        if point is None:
            return
        if self.drag_handler:
            self.drag_start = point
        elif self.click_handler:
            self.click_handler(point)

    def _release(self, event: tk.Event) -> None:
        if not self.drag_handler or self.drag_start is None:
            return
        end = self._point(event)
        start, self.drag_start = self.drag_start, None
        if end is not None and end != start:
            self.drag_handler(start, end)


class QuickFigurePanel(ttk.Frame):
    """Immediate 1xN figure workflow; no project/V10 identity verification required."""

    CATEGORY = "quick_figure"

    def __init__(self, parent: tk.Misc, viewer: Any, status: tk.StringVar) -> None:
        super().__init__(parent)
        self.viewer, self.status = viewer, status
        self.image_path: Path | None = None
        self.image: Image.Image | None = None
        self.csv_data: dict[str, Any] | None = None
        self.grid: dict[str, Any] | None = None
        self.grid_clicks: list[tuple[float, float]] = []
        self.crop_clicks: list[tuple[float, float]] = []
        saved = load_last(self.CATEGORY, {}) or {}
        self.description = tk.StringVar(value=saved.get("figure_description", ""))
        self.date = tk.StringVar(value=saved.get("date", ""))
        self.width = tk.StringVar(value=str(saved.get("crop_width", 130)))
        self.height = tk.StringVar(value=str(saved.get("crop_height", 546)))
        self.qc_required = tk.BooleanVar(value=bool(saved.get("qc_required", False)))
        self.preset_name = tk.StringVar()
        self.roi = [tk.StringVar() for _ in range(4)]
        self._build()
        self._bind_hotkeys()

    def _build(self) -> None:
        ttk.Label(
            self,
            text="Quick Figures: arbitrary image + minimal/V10-compatible CSV; no project verification.",
            wraplength=350,
        ).pack(anchor="w", padx=8, pady=7)
        row = ttk.Frame(self)
        row.pack(fill="x", padx=8)
        ttk.Button(row, text="Choose image…", command=self.choose_image).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Choose CSV…", command=self.choose_csv).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        for label, variable in (
            ("Quick figure description", self.description),
            ("Date", self.date),
        ):
            row = ttk.Frame(self)
            row.pack(fill="x", padx=8, pady=2)
            ttk.Label(row, text=label, width=22).pack(side="left")
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<FocusOut>", lambda _event: self.save_last_settings())
        orient = ttk.LabelFrame(self, text="Orientation / whole figure")
        orient.pack(fill="x", padx=8, pady=5)
        for text, operation in (
            ("↻ 90°", "rotate_90_cw"),
            ("↺ 90°", "rotate_90_ccw"),
            ("180°", "rotate_180"),
            ("Flip H", "flip_horizontal"),
            ("Flip V", "flip_vertical"),
        ):
            ttk.Button(
                orient, text=text, command=lambda op=operation: self.orient(op)
            ).pack(side="left", expand=True, fill="x")
        ttk.Button(
            self, text="Align: drag a top/bottom edge", command=self.start_alignment
        ).pack(fill="x", padx=8, pady=2)
        ttk.Button(
            self,
            text="Whole crop: click top-left then bottom-right",
            command=self.start_whole_crop,
        ).pack(fill="x", padx=8, pady=2)
        grid = ttk.LabelFrame(self, text="1 × N grid")
        grid.pack(fill="x", padx=8, pady=5)
        ttk.Button(
            grid, text="Register first + last well centres", command=self.start_grid
        ).pack(fill="x")
        qrow = ttk.Frame(grid)
        qrow.pack(fill="x", pady=2)
        ttk.Checkbutton(
            qrow,
            text="Require QC before export",
            variable=self.qc_required,
            command=self.save_last_settings,
        ).pack(side="left")
        ttk.Button(qrow, text="Accept QC", command=lambda: self.set_qc(True)).pack(
            side="right"
        )
        ttk.Button(qrow, text="Flag", command=lambda: self.set_qc(False)).pack(
            side="right"
        )
        dims = ttk.LabelFrame(self, text="Per-well rectangular crop")
        dims.pack(fill="x", padx=8, pady=5)
        row = ttk.Frame(dims)
        row.pack(fill="x")
        for label, variable in (("Width", self.width), ("Height", self.height)):
            ttk.Label(row, text=label).pack(side="left", padx=(4, 2))
            ttk.Entry(row, textvariable=variable, width=7).pack(side="left")
        ttk.Label(dims, text="ROI left, top, right, bottom").pack(anchor="w", padx=4)
        row = ttk.Frame(dims)
        row.pack(fill="x")
        for variable in self.roi:
            ttk.Entry(row, textvariable=variable, width=7).pack(
                side="left", expand=True, fill="x"
            )
        ttk.Button(
            dims, text="Calculate width/height from ROI", command=self.calculate_roi
        ).pack(fill="x")
        actions = ttk.LabelFrame(self, text="Preview / outputs")
        actions.pack(fill="x", padx=8, pady=5)
        ttk.Button(
            actions, text="Preview annotation", command=self.preview_annotation
        ).pack(fill="x")
        ttk.Button(
            actions, text="Save annotated figure…", command=self.save_annotation
        ).pack(fill="x")
        ttk.Button(
            actions, text="Export each well/culture…", command=self.export_cultures
        ).pack(fill="x")
        presets = ttk.Frame(self)
        presets.pack(fill="x", padx=8, pady=5)
        self.preset_box = ttk.Combobox(
            presets,
            textvariable=self.preset_name,
            state="readonly",
            values=list_presets(self.CATEGORY),
        )
        self.preset_box.pack(side="left", fill="x", expand=True)
        ttk.Button(presets, text="Load", command=self.load_named).pack(side="left")
        ttk.Button(presets, text="Save as…", command=self.save_named).pack(side="left")
        ttk.Button(self, text="Detach Quick Figures window", command=self.detach).pack(
            fill="x", padx=8, pady=(2, 8)
        )

    def _bind_hotkeys(self) -> None:
        root = self.winfo_toplevel()
        root.bind(
            "<Control-r>",
            lambda _event: self._hotkey(lambda: self.orient("rotate_90_cw")),
            add="+",
        )
        root.bind(
            "<Control-Shift-R>",
            lambda _event: self._hotkey(lambda: self.orient("rotate_90_ccw")),
            add="+",
        )
        root.bind(
            "<Control-l>", lambda _event: self._hotkey(self.start_alignment), add="+"
        )
        root.bind(
            "<Control-k>", lambda _event: self._hotkey(self.start_whole_crop), add="+"
        )
        root.bind("<Control-g>", lambda _event: self._hotkey(self.start_grid), add="+")
        root.bind(
            "<Control-e>", lambda _event: self._hotkey(self.export_cultures), add="+"
        )

    def _hotkey(self, action: Callable[[], None]) -> None:
        if self.winfo_ismapped():
            action()

    def settings(self) -> dict[str, Any]:
        return {
            "figure_description": self.description.get().strip(),
            "date": self.date.get().strip(),
            "crop_width": int(self.width.get()),
            "crop_height": int(self.height.get()),
            "qc_required": self.qc_required.get(),
        }

    def save_last_settings(self) -> None:
        try:
            save_last(self.CATEGORY, self.settings())
        except (OSError, ValueError):
            pass

    def choose_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose figure image",
            filetypes=[
                ("Images", "*.png *.tif *.tiff *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.image_path = Path(selected)
            self.image = Image.open(selected).convert("RGB")
            self.viewer.show(self.image)
            self.status.set(f"Quick Figure image: {self.image_path.name}")

    def choose_csv(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose quick label CSV",
            filetypes=[("CSV/TSV", "*.csv *.tsv"), ("All files", "*.*")],
        )
        if selected:
            try:
                self.csv_data = load_quick_csv(selected)
            except (csv.Error, OSError, UnicodeError, ValueError) as exc:
                messagebox.showerror("Quick CSV", str(exc))
                return
            for key, variable in (
                ("figure_description", self.description),
                ("date", self.date),
            ):
                if self.csv_data["metadata"].get(key) and not variable.get().strip():
                    variable.set(self.csv_data["metadata"][key])
            self.status.set(f"Loaded {len(self.csv_data['labels'])} well labels.")

    def orient(self, operation: str) -> None:
        if self.image is None:
            messagebox.showerror("Quick Figures", "Choose an image first.")
            return
        self.image = orient_image(self.image, operation)
        self.grid = None
        self.viewer.show(self.image)
        self.status.set(
            "Orientation applied in memory; re-register grid after geometry changes."
        )

    def start_alignment(self) -> None:
        if self.image is None:
            messagebox.showerror("Quick Figures", "Choose an image first.")
            return
        self.viewer.set_handlers(drag=self._alignment_dragged)
        self.status.set("Drag left-to-right along a top or bottom figure edge.")

    def _alignment_dragged(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> None:
        self.image, result = align_image_to_edge(self.image, start, end)
        self.grid = None
        self.viewer.set_handlers()
        self.viewer.show(self.image)
        self.status.set(
            f"Aligned by {result['angle_degrees']:.4f}° in memory; re-register grid."
        )

    def start_whole_crop(self) -> None:
        if self.image is None:
            messagebox.showerror("Quick Figures", "Choose an image first.")
            return
        self.crop_clicks = []
        self.viewer.set_handlers(click=self._crop_click)
        self.status.set("Click whole-figure crop top-left, then bottom-right.")

    def _crop_click(self, point: tuple[float, float]) -> None:
        self.crop_clicks.append(point)
        self.viewer.draw_points(self.crop_clicks)
        if len(self.crop_clicks) == 2:
            (x1, y1), (x2, y2) = self.crop_clicks
            box = (
                round(min(x1, x2)),
                round(min(y1, y2)),
                round(max(x1, x2)),
                round(max(y1, y2)),
            )
            if box[2] <= box[0] or box[3] <= box[1]:
                messagebox.showerror(
                    "Whole crop", "Crop must have positive width and height."
                )
                return
            self.image = self.image.crop(box)
            self.grid = None
            self.viewer.set_handlers()
            self.viewer.show(self.image)
            self.status.set(
                f"Whole crop applied in memory: {self.image.width} × {self.image.height}."
            )

    def start_grid(self) -> None:
        if self.image is None or self.csv_data is None:
            messagebox.showerror("Quick grid", "Choose an image and CSV first.")
            return
        self.grid_clicks = []
        self.viewer.set_handlers(click=self._grid_click)
        self.status.set("Click centre of first well, then centre of last well.")

    def _grid_click(self, point: tuple[float, float]) -> None:
        self.grid_clicks.append(point)
        self.viewer.draw_points(self.grid_clicks)
        if len(self.grid_clicks) == 2:
            self.grid = register_quick_grid(
                self.image_path or "quick-image",
                self.image.size,
                self.grid_clicks[0],
                self.grid_clicks[1],
                len(self.csv_data["labels"]),
            )
            self.viewer.set_handlers()
            self.viewer.draw_points(
                [(spot["x"], spot["y"]) for spot in self.grid["spots"]]
            )
            selected = filedialog.asksaveasfilename(
                title="Save reusable grid coordinates",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
            )
            if selected:
                save_quick_grid(self.grid, selected)
            self.status.set(
                f"Registered {len(self.grid['spots'])} reusable well centres; QC optional."
            )

    def set_qc(self, accepted: bool) -> None:
        if self.grid is None:
            messagebox.showerror("Quick grid", "Register a grid first.")
            return
        note = simpledialog.askstring("Grid QC", "Optional QC note:", parent=self) or ""
        self.grid = set_grid_qc(self.grid, accepted, note)
        self.status.set(f"Quick grid QC: {self.grid['provenance']['qc_status']}.")

    def calculate_roi(self) -> None:
        try:
            result = calculate_box_from_roi(*(float(value.get()) for value in self.roi))
        except ValueError as exc:
            messagebox.showerror("ROI calculator", str(exc))
            return
        self.width.set(str(result["width"]))
        self.height.set(str(result["height"]))
        self.save_last_settings()
        self.status.set(
            f"Calculated culture crop: {result['width']} × {result['height']} px."
        )

    def _ready(self) -> bool:
        if self.image is None or self.csv_data is None or self.grid is None:
            messagebox.showerror(
                "Quick Figures", "Choose image and CSV, then register the 1×N grid."
            )
            return False
        if (
            self.qc_required.get()
            and self.grid["provenance"]["qc_status"] != "ACCEPTED"
        ):
            messagebox.showerror(
                "Quick Figures", "This preset requires accepted grid QC before output."
            )
            return False
        return True

    def _labels(self) -> dict[str, str]:
        return {
            "figure_description": self.description.get().strip(),
            "date": self.date.get().strip(),
        }

    def preview_annotation(self) -> None:
        if not self._ready():
            return
        result = annotate_quick(
            self.image, self.csv_data, self.grid, labels_override=self._labels()
        )
        self.viewer.show(result["preview_image"])
        self.save_last_settings()
        self.status.set("Quick annotation preview; source remains unchanged.")

    def save_annotation(self) -> None:
        if not self._ready():
            return
        selected = filedialog.asksaveasfilename(
            title="Save annotated figure",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("TIFF", "*.tif")],
        )
        if selected:
            annotate_quick(
                self.image,
                self.csv_data,
                self.grid,
                labels_override=self._labels(),
                output_path=selected,
            )
            self.save_last_settings()
            self.status.set(f"Saved annotated figure: {selected}")

    def export_cultures(self) -> None:
        if not self._ready():
            return
        selected = filedialog.askdirectory(title="Choose per-well export folder")
        if selected:
            try:
                result = export_wells(
                    self.image,
                    self.grid,
                    self.csv_data["labels"],
                    int(self.width.get()),
                    int(self.height.get()),
                    selected,
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror("Well export", str(exc))
                return
            self.save_last_settings()
            self.status.set(
                f"Exported {len(result['outputs'])} wells to a new numbered run."
            )

    def save_named(self) -> None:
        name = simpledialog.askstring(
            "Quick Figure preset", "Preset name:", parent=self
        )
        if name:
            save_preset(self.CATEGORY, name, self.settings())
            self.preset_box.configure(values=list_presets(self.CATEGORY))
            self.preset_name.set(name)

    def load_named(self) -> None:
        if not self.preset_name.get():
            return
        settings = load_preset(self.CATEGORY, self.preset_name.get())
        self.description.set(settings.get("figure_description", ""))
        self.date.set(settings.get("date", ""))
        self.width.set(str(settings.get("crop_width", 130)))
        self.height.set(str(settings.get("crop_height", 546)))
        self.qc_required.set(bool(settings.get("qc_required", False)))
        self.save_last_settings()

    def detach(self) -> tk.Toplevel:
        window = tk.Toplevel(self)
        window.title("Quick Figures mini-applet")
        window.geometry("1050x700")
        body = ttk.Panedwindow(window, orient="horizontal")
        body.pack(fill="both", expand=True)
        viewer = QuickImageCanvas(body)
        controls = ttk.Frame(body, width=390)
        body.add(controls, weight=0)
        body.add(viewer, weight=1)
        status = tk.StringVar(value="Choose any figure image and a label CSV.")
        QuickFigurePanel(controls, viewer, status).pack(fill="both", expand=True)
        ttk.Label(window, textvariable=status, anchor="w").pack(
            fill="x", padx=8, pady=4
        )
        return window
