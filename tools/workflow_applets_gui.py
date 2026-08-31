from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from PIL import Image, ImageTk

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.annotation_settings_gui import AnnotationSettingsDialog
from tools.applet_presets import (
    list_presets,
    load_last,
    load_preset,
    save_last,
    save_preset,
)
from tools.applet_workflows import ProjectWorkflow
from tools.applets.batch_actions import (
    execute_automatic_batch,
    execute_grid_batch,
    plan_automatic_batch,
    plan_grid_directory,
)
from tools.applets.plate_crop import calibrate_crop_size
from tools.applets.quick_figure import calculate_box_from_roi
from tools.applets.v10_adapter import load_v10
from tools.project_lifecycle import (
    discover_experiment_folders,
    loose_image_files,
    match_experiment_folder,
    plan_layout_migration,
    plan_loose_image_import,
    subset_project_model,
)
from tools.project_paths import preferred_project_path
from tools.quick_figure_gui import QuickFigurePanel
from tools.windows_dpi import pointer_client_fraction


def next_image_uid(image_uids: list[str], current_uid: str) -> str | None:
    try:
        index = image_uids.index(current_uid)
    except ValueError:
        return None
    return image_uids[index + 1] if index + 1 < len(image_uids) else None


def next_pending_image_uid(
    images: dict[str, dict[str, Any]], current_uid: str, stage: str
) -> str | None:
    image_uids = list(images)
    try:
        start = image_uids.index(current_uid)
    except ValueError:
        return None
    terminal = {
        "orientation": {"accepted", "skipped"},
        "crop": {"accepted", "skipped"},
        "grid": {"accepted", "skipped"},
        "visibility": {"accepted", "skipped", "manual_review"},
        "annotation": {"accepted", "skipped"},
    }.get(stage)
    if terminal is None:
        return next_image_uid(image_uids, current_uid)
    ordered = image_uids[start + 1 :] + image_uids[:start]
    for uid in ordered:
        value = images[uid].get(stage)
        status = str(value.get("status", "")).casefold() if isinstance(value, dict) else ""
        if status not in terminal:
            return uid
    return None


def fitted_image_geometry(
    image_size: tuple[int, int], canvas_size: tuple[int, int]
) -> tuple[tuple[int, int], tuple[float, float], tuple[float, float]]:
    image_width, image_height = image_size
    canvas_width, canvas_height = canvas_size
    scale = min(canvas_width / image_width, canvas_height / image_height)
    shown = (
        max(1, round(image_width * scale)),
        max(1, round(image_height * scale)),
    )
    scales = (shown[0] / image_width, shown[1] / image_height)
    offset = ((canvas_width - shown[0]) / 2, (canvas_height - shown[1]) / 2)
    return shown, scales, offset


class ImageCanvas(ttk.Frame):
    """Fit-to-window image display with image-coordinate click/drag mapping."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self,
            width=820,
            height=560,
            background="#242424",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)
        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.scale = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset = (0.0, 0.0)
        self.render_canvas_size = (0, 0)
        self.coordinate_source = "not_sampled"
        self.coordinate_client_dimensions = (0, 0)
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

    def clear_overlays(self) -> None:
        self.canvas.delete("overlay")

    def set_handlers(
        self,
        *,
        click: Callable[[tuple[float, float]], None] | None = None,
        drag: Callable[[tuple[float, float], tuple[float, float]], None] | None = None,
    ) -> None:
        self.click_handler = click
        self.drag_handler = drag
        self.drag_start = None

    def canvas_to_image(self, x: float, y: float) -> tuple[float, float] | None:
        if self.image is None:
            return None
        current_size = (
            max(self.canvas.winfo_width(), 1),
            max(self.canvas.winfo_height(), 1),
        )
        if current_size != self.render_canvas_size:
            self._render()
        x_fraction, y_fraction, self.coordinate_source, dimensions = (
            pointer_client_fraction(self.canvas, x, y)
        )
        self.coordinate_client_dimensions = dimensions
        canvas_x = x_fraction * self.render_canvas_size[0]
        canvas_y = y_fraction * self.render_canvas_size[1]
        px = (canvas_x - self.offset[0]) / self.scale_x
        py = (canvas_y - self.offset[1]) / self.scale_y
        if 0 <= px < self.image.width and 0 <= py < self.image.height:
            return px, py
        return None

    def draw_points(self, points: list[tuple[float, float]]) -> None:
        self.clear_overlays()
        for index, (x, y) in enumerate(points, start=1):
            cx = self.offset[0] + x * self.scale_x
            cy = self.offset[1] + y * self.scale_y
            radius = 5
            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline="#00ffff",
                width=2,
                tags="overlay",
            )
            self.canvas.create_text(
                cx + 10,
                cy - 10,
                text=str(index),
                fill="#00ffff",
                anchor="sw",
                tags="overlay",
            )

    def draw_line(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        self.clear_overlays()
        coords = [
            self.offset[0] + start[0] * self.scale_x,
            self.offset[1] + start[1] * self.scale_y,
            self.offset[0] + end[0] * self.scale_x,
            self.offset[1] + end[1] * self.scale_y,
        ]
        self.canvas.create_line(*coords, fill="#00ffff", width=3, tags="overlay")

    def draw_box(self, box: dict[str, Any]) -> None:
        self.clear_overlays()
        self.canvas.create_rectangle(
            self.offset[0] + box["left"] * self.scale_x,
            self.offset[1] + box["top"] * self.scale_y,
            self.offset[0] + box["right"] * self.scale_x,
            self.offset[1] + box["bottom"] * self.scale_y,
            outline="#00ffff",
            width=3,
            tags="overlay",
        )

    def _render(self) -> None:
        self.canvas.delete("all")
        if self.image is None:
            self.canvas.create_text(
                410,
                280,
                text="Open a project and select an image",
                fill="#dddddd",
            )
            return
        width = max(self.canvas.winfo_width(), 100)
        height = max(self.canvas.winfo_height(), 100)
        self.render_canvas_size = (width, height)
        shown_size, scales, self.offset = fitted_image_geometry(
            self.image.size, (width, height)
        )
        self.scale_x, self.scale_y = scales
        self.scale = min(scales)
        shown = self.image.resize(
            shown_size,
            Image.Resampling.LANCZOS,
        )
        self.photo = ImageTk.PhotoImage(shown)
        self.canvas.create_image(*self.offset, image=self.photo, anchor="nw")

    def _press(self, event: tk.Event) -> None:
        point = self.canvas_to_image(event.x, event.y)
        if self.drag_handler and point is not None:
            self.drag_start = point
            return
        if self.click_handler and point is not None:
            self.click_handler(point)

    def _release(self, event: tk.Event) -> None:
        if not self.drag_handler or self.drag_start is None:
            return
        end = self.canvas_to_image(event.x, event.y)
        start, self.drag_start = self.drag_start, None
        if end is not None and end != start:
            self.drag_handler(start, end)


class WorkflowApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Workflow-integrated project applets")
        self.minsize(1080, 720)
        self.workflow: ProjectWorkflow | None = None
        self.image_uid = tk.StringVar()
        self.status = tk.StringVar(value="Create or open a V10 project state.")
        self.orientation_proposal: dict[str, Any] | None = None
        orientation_settings = load_last("orientation", {}) or {}
        self.orientation_input_mode = tk.StringVar(
            value=str(orientation_settings.get("input_mode", "line"))
        )
        self.orientation_auto_preview = tk.BooleanVar(
            value=bool(orientation_settings.get("auto_preview", True))
        )
        self.orientation_points: list[tuple[float, float]] = []
        self.calibration_points: list[tuple[float, float]] = []
        self.calibration_proposal: dict[str, Any] | None = None
        self.crop_points: list[tuple[float, float]] = []
        self.crop_proposal: dict[str, Any] | None = None
        self.crop_previewed = False
        self.calibration_source_dimensions: tuple[int, int] | None = None
        self.raw_root_var = tk.StringVar()
        setup_settings = load_last("project_setup", {}) or {}
        self.enable_rename = tk.BooleanVar(value=bool(setup_settings.get("enable_rename", True)))
        self.setup_review = tk.BooleanVar(value=bool(setup_settings.get("review_before_apply", True)))
        self.filename_date_style = tk.StringVar(value=str(setup_settings.get("filename_date_style", "yyyy.mm.dd")))
        self.rename_folder_date = tk.BooleanVar(value=bool(setup_settings.get("rename_folder_date", False)))
        self.auto_move_working = tk.BooleanVar(value=bool(setup_settings.get("auto_move_working", True)))
        self.auto_advance_images = tk.BooleanVar(
            value=bool(setup_settings.get("auto_advance_images", True))
        )
        self.csv_mode = tk.StringVar(value=str(setup_settings.get("csv_mode", "refreshable")))
        plate_crop_settings = load_last("plate_crop", {}) or {}
        self.crop_rounding_enabled = tk.BooleanVar(
            value=bool(plate_crop_settings.get("rounding_enabled", True))
        )
        self.crop_rounding_increment = tk.StringVar(
            value=str(plate_crop_settings.get("rounding_increment", 50))
        )
        self.crop_rounding_direction = tk.StringVar(
            value=str(plate_crop_settings.get("rounding_direction", "down"))
        )
        self.crop_margin_value = tk.StringVar(
            value=str(plate_crop_settings.get("margin_value", 0))
        )
        self.crop_margin_unit = tk.StringVar(
            value=str(plate_crop_settings.get("margin_unit", "pixels"))
        )
        self.crop_auto_preview = tk.BooleanVar(
            value=bool(plate_crop_settings.get("auto_preview", True))
        )
        self.crop_exact_side = tk.StringVar(
            value=str(plate_crop_settings.get("exact_side_pixels", ""))
        )
        self.crop_calibration_id = tk.StringVar(
            value=str(plate_crop_settings.get("calibration_id", ""))
        )
        self.setup_preview: dict[str, Any] | None = None
        self.setup_signature: tuple[str, bool, str] | None = None
        culture_settings = load_last("culture_crop", {}) or {}
        self.crop_export_tier = tk.StringVar(value=str(culture_settings.get("tier", "Unprocessed")))
        self.crop_export_source = tk.StringVar(value=str(culture_settings.get("source_kind", "Cropped")))
        self.crop_export_top = tk.BooleanVar(value=bool(culture_settings.get("top", True)))
        self.crop_export_low = tk.BooleanVar(value=bool(culture_settings.get("low", True)))
        self.crop_export_columns = tk.StringVar(value=str(culture_settings.get("columns", "")))
        self.crop_export_width = tk.StringVar(value=str(culture_settings.get("width", 130)))
        self.crop_export_height = tk.StringVar(value=str(culture_settings.get("height", 546)))
        self.crop_export_preset = tk.StringVar()
        self.crop_export_roi = [tk.StringVar() for _ in range(4)]
        self.crop_export_plan: dict[str, Any] | None = None
        self.crop_export_signature: tuple[Any, ...] | None = None
        self.matrix_candidates: dict[str, dict[str, Any]] = {}
        matrix_settings = load_last("mixed_matrix", {}) or {}
        self.matrix_layout_mode = tk.StringVar(value=str(matrix_settings.get("layout_mode", "Selected crops (one column)")))
        self.matrix_tile_width = tk.StringVar(value=str(matrix_settings.get("tile_width", "")))
        self.matrix_tile_height = tk.StringVar(value=str(matrix_settings.get("tile_height", "")))
        self.matrix_plan: dict[str, Any] | None = None
        self.matrix_signature: tuple[Any, ...] | None = None
        visibility_settings = load_last("visibility", {}) or {}
        self.visibility_preset = tk.StringVar(value=str(visibility_settings.get("preset", "background_aware_linear")))
        self.visibility_proposal: dict[str, Any] | None = None
        self.annotation_proposal: dict[str, Any] | None = None
        self.annotation_labels = {
            key: tk.StringVar()
            for key in ("date", "figure_description", "plate", "condition", "session", "media")
        }
        self.annotation_label_enabled = {key: tk.BooleanVar(value=True) for key in self.annotation_labels}
        self.annotation_header_enabled = tk.BooleanVar(value=True)
        self.annotation_header_grouped = tk.BooleanVar(value=True)
        self.annotation_in_image_enabled = tk.BooleanVar(value=False)
        self.annotation_in_image_grouped = tk.BooleanVar(value=True)
        self.annotation_preset_settings = load_last("annotation", {}) or {}
        self.annotation_source = tk.StringVar(value=str(self.annotation_preset_settings.get("source_kind", "Automatic")))
        self.annotation_strain_size = tk.StringVar(value="18")
        self.annotation_vertical_size = tk.StringVar(value="18")
        self.annotation_rotation = tk.StringVar(value="90")
        self.batch_plan: dict[str, Any] | None = None
        self.batch_queue: list[str] = []
        self.batch_queue_stage: str | None = None
        self.batch_queue_index = 0
        self._sync_annotation_controls()
        self._build()
        self.bind("<Alt-o>", lambda _event: self.start_orientation())
        self.bind("<Alt-c>", lambda _event: self.start_crop_placement())
        self.bind("<Alt-b>", lambda _event: self.refresh_batch_images())
        self.bind("<KeyPress>", self._letter_hotkey)

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Create from V10…", command=self.create_project).pack(
            side="left"
        )
        ttk.Button(top, text="Prepare one folder…", command=self.prepare_one_folder).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(top, text="Prepare parent…", command=self.prepare_parent_folder).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(top, text="Open project…", command=self.open_project).pack(
            side="left", padx=(6, 0)
        )
        self.hotkey_help_button = ttk.Button(
            top, text="Hotkeys ▸", command=self._toggle_hotkey_help
        )
        self.hotkey_help_button.pack(side="right")
        ttk.Label(top, text="Image UID").pack(side="left", padx=(18, 5))
        self.image_picker = ttk.Combobox(
            top, textvariable=self.image_uid, state="readonly", width=34
        )
        self.image_picker.pack(side="left")
        self.image_picker.bind("<<ComboboxSelected>>", self.load_selected_source)

        self.hotkey_help_frame = ttk.LabelFrame(self, text="Keyboard shortcuts")
        ttk.Label(
            self.hotkey_help_frame,
            text=(
                "Common stage keys: X start/retry · V preview · Z accept/export · C skip/next. "
                "Orientation: A line/two-point. Plate crop: A recalibrate · S accept measured size · D accept exact size. "
                "Grid: X find+attach · V preview matches · Z attach one. Culture: X/V preview · Z export. "
                "Visibility: A flag. Annotation: A styles. Matrix: X refresh.\n"
                "Quick Figures: X align · V preview annotation · Z save annotation · C export wells · "
                "A accept QC · F flag QC · Q whole crop · W grid · E/R rotate. "
                "Batch: X refresh · A select all · Q/W orientation/crop queues · E/R/F plan "
                "culture/visibility/annotation · V preview setup · Z accept plan · S apply setup · G grids. "
                "Shortcuts are ignored while typing in a field."
            ),
            wraplength=1040,
            justify="left",
        ).pack(fill="x", padx=8, pady=5)

        body = ttk.Panedwindow(self, orient="horizontal")
        self.body = body
        body.pack(fill="both", expand=True, padx=8)
        controls = ttk.Frame(body, width=390)
        body.add(controls, weight=0)
        self.viewer = ImageCanvas(body)
        body.add(self.viewer, weight=1)

        notebook = ttk.Notebook(controls)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True)
        setup = ttk.Frame(notebook)
        orientation = ttk.Frame(notebook)
        crop = ttk.Frame(notebook)
        grid = ttk.Frame(notebook)
        culture_crops = ttk.Frame(notebook)
        visibility = ttk.Frame(notebook)
        annotation = ttk.Frame(notebook)
        mixed_matrix = ttk.Frame(notebook)
        quick_figures = ttk.Frame(notebook)
        batch = ttk.Frame(notebook)
        notebook.add(setup, text="Setup")
        notebook.add(orientation, text="Orientation")
        notebook.add(crop, text="Plate crop")
        notebook.add(grid, text="Grid asset")
        notebook.add(culture_crops, text="Culture crops")
        notebook.add(visibility, text="Visibility")
        notebook.add(annotation, text="Annotation")
        notebook.add(mixed_matrix, text="Mixed matrix")
        notebook.add(quick_figures, text="Quick Figures")
        notebook.add(batch, text="Batch")
        self.quick_figure_panel = QuickFigurePanel(quick_figures, self.viewer, self.status)
        self.quick_figure_panel.pack(fill="both", expand=True)

        ttk.Label(
            setup,
            text=(
                "Preview V10 reconciliation before copying Working derivatives. "
                "Missing expected images remain valid; collisions fail closed."
            ),
            wraplength=360,
        ).pack(anchor="w", padx=8, pady=8)
        raw_row = ttk.Frame(setup)
        raw_row.pack(fill="x", padx=8, pady=3)
        ttk.Entry(raw_row, textvariable=self.raw_root_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(raw_row, text="…", width=3, command=self.choose_raw_root).pack(
            side="left", padx=(4, 0)
        )
        ttk.Checkbutton(
            setup, text="Use V10 working filenames", variable=self.enable_rename
        ).pack(anchor="w", padx=8, pady=3)
        ttk.Checkbutton(
            setup, text="Review planned changes before applying", variable=self.setup_review
        ).pack(anchor="w", padx=8, pady=3)
        date_row = ttk.Frame(setup)
        date_row.pack(fill="x", padx=8, pady=3)
        ttk.Label(date_row, text="Filename dates").pack(side="left")
        ttk.Combobox(
            date_row,
            textvariable=self.filename_date_style,
            state="readonly",
            values=("v10", "yyyy.mm.dd"),
            width=14,
        ).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(
            setup, text="Rename experiment-folder date", variable=self.rename_folder_date
        ).pack(anchor="w", padx=8, pady=3)
        ttk.Checkbutton(
            setup, text="Move Working beneath Cropped when complete", variable=self.auto_move_working
        ).pack(anchor="w", padx=8, pady=3)
        ttk.Checkbutton(
            setup,
            text="Automatically advance to the next image",
            variable=self.auto_advance_images,
        ).pack(anchor="w", padx=8, pady=3)
        setup_actions = ttk.Frame(setup)
        setup_actions.pack(fill="x", padx=8, pady=3)
        ttk.Button(
            setup_actions, text="Preview", command=self.preview_project_setup
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(setup_actions, text="Apply", command=self.apply_project_setup).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        lifecycle_actions = ttk.Frame(setup)
        lifecycle_actions.pack(fill="x", padx=8, pady=3)
        ttk.Button(lifecycle_actions, text="Upgrade old folders…", command=self.migrate_project_layout).pack(side="left", fill="x", expand=True)
        ttk.Button(lifecycle_actions, text="Mark Working complete", command=self.mark_working_complete).pack(side="left", fill="x", expand=True, padx=(5, 0))
        ttk.Button(setup, text="Rename project-folder date now", command=self.rename_project_date_now).pack(fill="x", padx=8, pady=3)
        csv_row = ttk.Frame(setup)
        csv_row.pack(fill="x", padx=8, pady=3)
        ttk.Combobox(csv_row, textvariable=self.csv_mode, state="readonly", values=("refreshable", "pinned"), width=12).pack(side="left")
        ttk.Button(csv_row, text="Keep current", command=self.keep_current_csvs).pack(side="left", padx=(4, 0))
        ttk.Button(csv_row, text="Refresh V10", command=self.refresh_v10_csvs).pack(side="left", padx=(4, 0))
        ttk.Button(csv_row, text="Compare", command=self.compare_v10_csvs).pack(side="left", padx=(4, 0))
        ttk.Button(setup, text="Save setup choices as defaults", command=self.save_setup_defaults).pack(fill="x", padx=8, pady=3)
        self.setup_tree = ttk.Treeview(
            setup,
            columns=("raw", "uid", "working", "status"),
            show="headings",
            height=8,
        )
        for key, label, width in (
            ("raw", "Raw", 105),
            ("uid", "UID", 70),
            ("working", "Working", 105),
            ("status", "Disposition", 105),
        ):
            self.setup_tree.heading(key, text=label)
            self.setup_tree.column(key, width=width, stretch=True)
        self.setup_tree.pack(fill="both", expand=True, padx=8, pady=(5, 8))
        ttk.Label(
            orientation,
            text="Mark two locations that should form a horizontal plate edge, preview, then accept.",
            wraplength=245,
        ).pack(anchor="w", padx=8, pady=8)
        orientation_mode = ttk.Frame(orientation)
        orientation_mode.pack(fill="x", padx=8, pady=3)
        ttk.Radiobutton(
            orientation_mode,
            text="Drag line",
            variable=self.orientation_input_mode,
            value="line",
        ).pack(side="left")
        ttk.Radiobutton(
            orientation_mode,
            text="Click two points",
            variable=self.orientation_input_mode,
            value="two_points",
        ).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(
            orientation,
            text="Automatically preview after input",
            variable=self.orientation_auto_preview,
        ).pack(anchor="w", padx=8, pady=3)
        ttk.Button(
            orientation, text="Start / retry (X)", command=self.start_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Preview correction (V)", command=self.preview_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Accept orientation (Z)", command=self.accept_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Skip orientation (C)", command=self.skip_orientation
        ).pack(fill="x", padx=8, pady=3)

        ttk.Label(
            crop,
            text=(
                "Calibrate size once using left, right, top, bottom clicks. "
                "Place each crop with independent left and top clicks."
            ),
            wraplength=245,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Button(
            crop, text="Recalibrate size (4 clicks, A)", command=self.start_calibration
        ).pack(fill="x", padx=8, pady=3)
        preset_row = ttk.Frame(crop)
        preset_row.pack(fill="x", padx=8, pady=3)
        ttk.Label(preset_row, text="Saved size preset").pack(side="left")
        self.crop_calibration_box = ttk.Combobox(
            preset_row,
            textvariable=self.crop_calibration_id,
            state="readonly",
            width=18,
        )
        self.crop_calibration_box.pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        self.crop_calibration_box.bind(
            "<<ComboboxSelected>>", self._crop_calibration_selected
        )
        crop_size_options = ttk.LabelFrame(crop, text="Reusable size rule")
        crop_size_options.pack(fill="x", padx=8, pady=3)
        ttk.Checkbutton(
            crop_size_options,
            text="Round measured size",
            variable=self.crop_rounding_enabled,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        ttk.Label(crop_size_options, text="Increment").grid(
            row=1, column=0, sticky="w", padx=4, pady=2
        )
        ttk.Entry(
            crop_size_options, textvariable=self.crop_rounding_increment, width=8
        ).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        ttk.Combobox(
            crop_size_options,
            textvariable=self.crop_rounding_direction,
            state="readonly",
            values=("down", "nearest", "up"),
            width=10,
        ).grid(row=1, column=2, sticky="ew", padx=4, pady=2)
        ttk.Label(crop_size_options, text="Margin / side").grid(
            row=2, column=0, sticky="w", padx=4, pady=2
        )
        ttk.Entry(
            crop_size_options, textvariable=self.crop_margin_value, width=8
        ).grid(row=2, column=1, sticky="ew", padx=4, pady=2)
        ttk.Combobox(
            crop_size_options,
            textvariable=self.crop_margin_unit,
            state="readonly",
            values=("pixels", "percent"),
            width=10,
        ).grid(row=2, column=2, sticky="ew", padx=4, pady=2)
        ttk.Label(crop_size_options, text="Exact final side").grid(
            row=3, column=0, sticky="w", padx=4, pady=2
        )
        ttk.Entry(
            crop_size_options, textvariable=self.crop_exact_side, width=8
        ).grid(row=3, column=1, sticky="ew", padx=4, pady=2)
        ttk.Label(crop_size_options, text="px (optional)").grid(
            row=3, column=2, sticky="w", padx=4, pady=2
        )
        crop_size_options.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            crop,
            text="Automatically preview after crop placement",
            variable=self.crop_auto_preview,
        ).pack(anchor="w", padx=8, pady=3)
        self.calibration_label = ttk.Label(crop, text="No accepted calibration")
        self.calibration_label.pack(anchor="w", padx=8, pady=3)
        ttk.Button(
            crop, text="Accept size calibration (S)", command=self.accept_calibration
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            crop,
            text="Accept exact final side — no clicks (D)",
            command=self.accept_exact_calibration,
        ).pack(fill="x", padx=8, pady=3)
        ttk.Separator(crop).pack(fill="x", padx=8, pady=8)
        ttk.Button(
            crop, text="Place / retry crop (X)", command=self.start_crop_placement
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(crop, text="Preview crop (V)", command=self.preview_crop).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(crop, text="Accept crop (Z)", command=self.accept_crop).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(
            crop, text="Retry placement", command=self.start_crop_placement
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(crop, text="Skip crop (C)", command=self.skip_crop).pack(
            fill="x", padx=8, pady=3
        )

        ttk.Label(
            grid,
            text=(
                "Attach the accepted GridCoordinateAsset written by the proven "
                "four-point route. Later applets reuse it without new clicks."
            ),
            wraplength=245,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Button(grid, text="Attach grid asset… (Z)", command=self.attach_grid).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(grid, text="Find and attach project grids (X)", command=self.auto_attach_grids).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(grid, text="Preview grid matches (V)", command=self.preview_grid_discovery).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(grid, text="Skip to next image (C)", command=self.skip_current_grid).pack(
            fill="x", padx=8, pady=3
        )
        self.grid_label = ttk.Label(grid, text="No current grid asset", wraplength=245)
        self.grid_label.pack(anchor="w", padx=8, pady=6)
        ttk.Label(
            culture_crops,
            text=(
                "Export exact Top/Low cultures later from the accepted grid. "
                "Preview validates every rectangle before any file is written."
            ),
            wraplength=360,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Label(culture_crops, text="Source stage").pack(anchor="w", padx=8)
        ttk.Combobox(
            culture_crops,
            textvariable=self.crop_export_source,
            state="readonly",
            values=("Working", "Cropped", "Processed"),
        ).pack(fill="x", padx=8, pady=3)
        states_row = ttk.Frame(culture_crops)
        states_row.pack(fill="x", padx=8, pady=3)
        ttk.Checkbutton(states_row, text="Top", variable=self.crop_export_top).pack(
            side="left"
        )
        ttk.Checkbutton(states_row, text="Low", variable=self.crop_export_low).pack(
            side="left", padx=(10, 0)
        )
        columns_row = ttk.Frame(culture_crops)
        columns_row.pack(fill="x", padx=8, pady=3)
        ttk.Label(columns_row, text="Columns", width=10).pack(side="left")
        ttk.Entry(columns_row, textvariable=self.crop_export_columns).pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(
            culture_crops,
            text="Blank = all; examples: 1,3-5,10",
        ).pack(anchor="w", padx=8)
        dimensions_row = ttk.Frame(culture_crops)
        dimensions_row.pack(fill="x", padx=8, pady=3)
        ttk.Label(dimensions_row, text="Width").pack(side="left")
        ttk.Entry(dimensions_row, textvariable=self.crop_export_width, width=7).pack(
            side="left", padx=(4, 12)
        )
        ttk.Label(dimensions_row, text="Height").pack(side="left")
        ttk.Entry(dimensions_row, textvariable=self.crop_export_height, width=7).pack(
            side="left", padx=(4, 0)
        )
        ttk.Label(culture_crops, text="Fiji ROI: left, top, right, bottom").pack(anchor="w", padx=8)
        roi_row = ttk.Frame(culture_crops)
        roi_row.pack(fill="x", padx=8, pady=2)
        for variable in self.crop_export_roi:
            ttk.Entry(roi_row, textvariable=variable, width=7).pack(side="left", fill="x", expand=True)
        ttk.Button(culture_crops, text="Calculate width/height from ROI", command=self.calculate_culture_crop_size).pack(fill="x", padx=8, pady=2)
        preset_row = ttk.Frame(culture_crops)
        preset_row.pack(fill="x", padx=8, pady=2)
        self.crop_export_preset_box = ttk.Combobox(preset_row, textvariable=self.crop_export_preset, state="readonly", values=list_presets("culture_crop"))
        self.crop_export_preset_box.pack(side="left", fill="x", expand=True)
        ttk.Button(preset_row, text="Load size", command=self.load_culture_crop_preset).pack(side="left", padx=(4, 0))
        ttk.Button(preset_row, text="Save size…", command=self.save_culture_crop_preset).pack(side="left", padx=(4, 0))
        crop_actions = ttk.Frame(culture_crops)
        crop_actions.pack(fill="x", padx=8, pady=5)
        ttk.Button(
            crop_actions,
            text="Preview plan (X or V)",
            command=self.preview_culture_crop_export,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            crop_actions,
            text="Export (Z)",
            command=self.accept_culture_crop_export,
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))
        ttk.Button(
            culture_crops,
            text="Skip to next image (C)",
            command=self.skip_culture_crop_export,
        ).pack(fill="x", padx=8, pady=(0, 3))
        self.crop_export_tree = ttk.Treeview(
            culture_crops,
            columns=("state", "column", "strain", "rectangle"),
            show="headings",
            height=12,
        )
        for key, label, width in (
            ("state", "State", 55),
            ("column", "Col", 40),
            ("strain", "Strain", 90),
            ("rectangle", "Rectangle", 150),
        ):
            self.crop_export_tree.heading(key, text=label)
            self.crop_export_tree.column(key, width=width, stretch=True)
        self.crop_export_tree.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        ttk.Label(
            visibility,
            text=(
                "Use the accepted grid as the measurement ROI, preview a whole-image "
                "display derivative, then accept or flag for manual review."
            ),
            wraplength=360,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Combobox(
            visibility,
            textvariable=self.visibility_preset,
            state="readonly",
            values=("background_aware_linear", "gamma_boost"),
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility, text="Start / retry preview (X or V)", command=self.preview_visibility
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility,
            text="Accept processed derivative (Z)",
            command=self.accept_visibility,
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility, text="Flag for manual review (A)", command=self.flag_visibility
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility, text="Skip visibility (C)", command=self.skip_visibility
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility, text="Return to source", command=self.load_selected_source
        ).pack(fill="x", padx=8, pady=3)

        ttk.Label(
            annotation,
            text=(
                "Automatically place V10 layout labels from saved grid coordinates. "
                "Adjust the lightweight preset, preview, then accept."
            ),
            wraplength=360,
        ).pack(anchor="w", padx=8, pady=8)
        master = ttk.Frame(annotation)
        master.pack(fill="x", padx=8, pady=2)
        ttk.Checkbutton(master, text="Master header", variable=self.annotation_header_enabled).pack(side="left")
        ttk.Checkbutton(master, text="Grouped", variable=self.annotation_header_grouped).pack(side="left")
        ttk.Checkbutton(master, text="Duplicate in image", variable=self.annotation_in_image_enabled).pack(side="left")
        ttk.Checkbutton(master, text="Grouped", variable=self.annotation_in_image_grouped).pack(side="left")
        for key, label in (
            ("date", "Date"),
            ("figure_description", "Figure description"),
            ("plate", "Plate"),
            ("condition", "Condition"),
            ("session", "Session"),
            ("media", "Media"),
        ):
            row = ttk.Frame(annotation)
            row.pack(fill="x", padx=8, pady=2)
            command = self._figure_description_toggled if key == "figure_description" else None
            ttk.Checkbutton(row, text=label, width=17, variable=self.annotation_label_enabled[key], command=command).pack(side="left")
            ttk.Entry(row, textvariable=self.annotation_labels[key]).pack(side="left", fill="x", expand=True)
        for variable, label in (
            (self.annotation_strain_size, "Strain font"),
            (self.annotation_vertical_size, "Vertical font"),
            (self.annotation_rotation, "Strain rotation"),
        ):
            row = ttk.Frame(annotation)
            row.pack(fill="x", padx=8, pady=2)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=variable, width=8).pack(side="left")
        source_group = ttk.LabelFrame(annotation, text="Image source")
        source_group.pack(fill="x", padx=8, pady=(6, 3))
        for label in ("Automatic", "Processed", "Cropped", "Working"):
            ttk.Radiobutton(source_group, text=label, value=label, variable=self.annotation_source).pack(side="left")
        ttk.Button(annotation, text="Advanced styles / presets… (A)", command=self.open_annotation_settings).pack(fill="x", padx=8, pady=(8, 3))
        ttk.Button(
            annotation, text="Start / retry preview (X or V)", command=self.preview_annotation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            annotation,
            text="Accept annotated derivative (Z)",
            command=self.accept_annotation,
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            annotation, text="Skip annotation (C)", command=self.skip_annotation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            annotation, text="Return to source", command=self.load_selected_source
        ).pack(fill="x", padx=8, pady=3)

        ttk.Label(
            mixed_matrix,
            text=(
                "Select one verified crop for every strain × image cell. "
                "Top and Low may be mixed within the same matrix."
            ),
            wraplength=360,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Combobox(
            mixed_matrix,
            textvariable=self.matrix_layout_mode,
            state="readonly",
            values=(
                "Selected crops (one column)",
                "Strain × image grid",
            ),
        ).pack(fill="x", padx=8, pady=3)
        matrix_dimensions = ttk.Frame(mixed_matrix)
        matrix_dimensions.pack(fill="x", padx=8, pady=3)
        ttk.Label(matrix_dimensions, text="Tile width").pack(side="left")
        ttk.Entry(matrix_dimensions, textvariable=self.matrix_tile_width, width=7).pack(
            side="left", padx=(4, 12)
        )
        ttk.Label(matrix_dimensions, text="height").pack(side="left")
        ttk.Entry(
            matrix_dimensions, textvariable=self.matrix_tile_height, width=7
        ).pack(side="left", padx=(4, 0))
        ttk.Label(
            mixed_matrix,
            text="Leave both tile fields blank to preserve the first crop size.",
        ).pack(anchor="w", padx=8)
        matrix_actions = ttk.Frame(mixed_matrix)
        matrix_actions.pack(fill="x", padx=8, pady=5)
        ttk.Button(
            matrix_actions,
            text="Refresh crops (X)",
            command=self.refresh_mixed_matrix_candidates,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            matrix_actions,
            text="Preview selected (V)",
            command=self.preview_mixed_tier_matrix,
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))
        ttk.Button(
            mixed_matrix,
            text="Export previewed matrix (Z)",
            command=self.accept_mixed_tier_matrix,
        ).pack(fill="x", padx=8, pady=(0, 5))
        self.matrix_tree = ttk.Treeview(
            mixed_matrix,
            columns=("state", "source", "strain", "image", "context"),
            show="headings",
            selectmode="extended",
            height=16,
        )
        for key, label, width in (
            ("state", "Top/Low", 60),
            ("source", "Source", 80),
            ("strain", "Strain", 80),
            ("image", "Image UID", 90),
            ("context", "Experiment / Set / Condition / Date", 170),
        ):
            self.matrix_tree.heading(key, text=label)
            self.matrix_tree.column(key, width=width, stretch=True)
        self.matrix_tree.pack(fill="both", expand=True, padx=8, pady=(2, 8))

        ttk.Label(batch, text="Select images. Automatic stages preflight the entire selection before confirmation; orientation and plate crop advance as manual queues.", wraplength=360).pack(anchor="w", padx=8, pady=7)
        batch_actions = ttk.Frame(batch)
        batch_actions.pack(fill="x", padx=8)
        ttk.Button(batch_actions, text="Refresh", command=self.refresh_batch_images).pack(side="left", fill="x", expand=True)
        ttk.Button(batch_actions, text="Select all", command=self.select_all_batch_images).pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.batch_tree = ttk.Treeview(batch, columns=("uid", "orientation", "crop", "grid", "visibility", "annotation"), show="headings", selectmode="extended", height=12)
        for key, label, width in (("uid", "Image UID", 100), ("orientation", "Orient", 50), ("crop", "Crop", 50), ("grid", "Grid", 50), ("visibility", "Visibility", 60), ("annotation", "Annotation", 70)):
            self.batch_tree.heading(key, text=label); self.batch_tree.column(key, width=width, stretch=True)
        self.batch_tree.pack(fill="both", expand=True, padx=8, pady=5)
        manual = ttk.LabelFrame(batch, text="Manual queues")
        manual.pack(fill="x", padx=8, pady=3)
        ttk.Button(manual, text="Orientation queue (Alt+O current)", command=lambda: self.start_manual_batch("orientation")).pack(fill="x")
        ttk.Button(manual, text="Plate-crop queue (Alt+C current)", command=lambda: self.start_manual_batch("crop")).pack(fill="x")
        automatic = ttk.LabelFrame(batch, text="Dry-run then accept")
        automatic.pack(fill="x", padx=8, pady=3)
        for label, stage in (("Plan culture crops", "culture"), ("Plan visibility", "visibility"), ("Plan annotation", "annotation")):
            ttk.Button(automatic, text=label, command=lambda value=stage: self.plan_selected_batch(value)).pack(side="left", fill="x", expand=True)
        ttk.Button(batch, text="Accept current batch plan", command=self.accept_batch_plan).pack(fill="x", padx=8, pady=3)
        ttk.Button(batch, text="Attach matching grids from folder…", command=self.batch_attach_grids).pack(fill="x", padx=8, pady=3)
        setup_batch = ttk.Frame(batch)
        setup_batch.pack(fill="x", padx=8, pady=3)
        ttk.Button(setup_batch, text="Preview all-image setup", command=self.preview_project_setup).pack(side="left", fill="x", expand=True)
        ttk.Button(setup_batch, text="Apply all-image setup", command=self.apply_project_setup).pack(side="left", fill="x", expand=True)

        ttk.Label(self, textvariable=self.status, wraplength=1040).pack(
            fill="x", padx=8, pady=(6, 8)
        )

    def _run(self, action: Callable[[], Any]) -> Any:
        try:
            return action()
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            tk.TclError,
        ) as exc:
            messagebox.showerror("Workflow applets", str(exc))
            self.status.set(str(exc))
            return None

    def _toggle_hotkey_help(self) -> None:
        if self.hotkey_help_frame.winfo_manager():
            self.hotkey_help_frame.pack_forget()
            self.hotkey_help_button.configure(text="Hotkeys ▸")
            return
        self.hotkey_help_frame.pack(
            fill="x", padx=8, pady=(0, 4), before=self.body
        )
        self.hotkey_help_button.configure(text="Hotkeys ▾")

    def _letter_hotkey(self, event: tk.Event) -> str | None:
        if event.widget.winfo_toplevel() is not self:
            return None
        if int(getattr(event, "state", 0)) & 0x000C:
            return None
        key = str(getattr(event, "keysym", "")).casefold()
        if key not in {"a", "c", "d", "e", "f", "g", "q", "r", "s", "v", "w", "x", "z"}:
            return None
        focus = self.focus_get()
        if focus is not None and focus.winfo_class() in {
            "Entry",
            "TEntry",
            "Text",
            "Spinbox",
            "TSpinbox",
            "TCombobox",
            "Treeview",
            "Listbox",
        }:
            return None
        tab = str(self.notebook.tab(self.notebook.select(), "text"))
        if self._stage_hotkey(tab, key):
            return "break"
        return None

    def _stage_hotkey(self, tab: str, key: str) -> bool:
        common: dict[str, dict[str, Callable[[], Any]]] = {
            "Setup": {
                "x": self.preview_project_setup,
                "v": self.preview_project_setup,
                "z": self.apply_project_setup,
            },
            "Orientation": {
                "x": self.start_orientation,
                "v": self.preview_orientation,
                "z": self.accept_orientation,
                "c": self.skip_orientation,
                "a": self._toggle_orientation_mode,
            },
            "Plate crop": {
                "x": self.start_crop_placement,
                "v": self.preview_crop,
                "z": self.accept_crop,
                "c": self.skip_crop,
                "a": self.start_calibration,
                "s": self.accept_calibration,
                "d": self.accept_exact_calibration,
            },
            "Grid asset": {
                "x": self.auto_attach_grids,
                "v": self.preview_grid_discovery,
                "z": self.attach_grid,
                "c": self.skip_current_grid,
            },
            "Culture crops": {
                "x": self.preview_culture_crop_export,
                "v": self.preview_culture_crop_export,
                "z": self.accept_culture_crop_export,
                "c": self.skip_culture_crop_export,
            },
            "Visibility": {
                "x": self.preview_visibility,
                "v": self.preview_visibility,
                "z": self.accept_visibility,
                "c": self.skip_visibility,
                "a": self.flag_visibility,
            },
            "Annotation": {
                "x": self.preview_annotation,
                "v": self.preview_annotation,
                "z": self.accept_annotation,
                "c": self.skip_annotation,
                "a": self.open_annotation_settings,
            },
            "Mixed matrix": {
                "x": self.refresh_mixed_matrix_candidates,
                "v": self.preview_mixed_tier_matrix,
                "z": self.accept_mixed_tier_matrix,
            },
            "Quick Figures": {
                "x": self.quick_figure_panel.start_alignment,
                "v": self.quick_figure_panel.preview_annotation,
                "z": self.quick_figure_panel.save_annotation,
                "c": self.quick_figure_panel.export_cultures,
                "a": lambda: self.quick_figure_panel.set_qc(True),
                "f": lambda: self.quick_figure_panel.set_qc(False),
                "q": self.quick_figure_panel.start_whole_crop,
                "w": self.quick_figure_panel.start_grid,
                "e": lambda: self.quick_figure_panel.orient("rotate_90_ccw"),
                "r": lambda: self.quick_figure_panel.orient("rotate_90_cw"),
            },
            "Batch": {
                "x": self.refresh_batch_images,
                "a": self.select_all_batch_images,
                "q": lambda: self.start_manual_batch("orientation"),
                "w": lambda: self.start_manual_batch("crop"),
                "e": lambda: self.plan_selected_batch("culture"),
                "r": lambda: self.plan_selected_batch("visibility"),
                "f": lambda: self.plan_selected_batch("annotation"),
                "v": self.preview_project_setup,
                "z": self.accept_batch_plan,
                "s": self.apply_project_setup,
                "g": self.batch_attach_grids,
            },
        }
        action = common.get(tab, {}).get(key)
        if action is None:
            return False
        self._run(action)
        return True

    def _toggle_orientation_mode(self) -> None:
        self.orientation_input_mode.set(
            "two_points"
            if self.orientation_input_mode.get() == "line"
            else "line"
        )
        self.start_orientation()

    def create_project(self) -> None:
        workbook = filedialog.askopenfilename(
            title="Select V10 workbook",
            filetypes=[("Excel workbook", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if not workbook:
            return
        root = filedialog.askdirectory(title="Select the project root folder")
        if not root:
            return
        workflow = self._run(lambda: ProjectWorkflow.create_from_v10(workbook, root))
        if workflow:
            self._activate(workflow)

    def _setup_settings_value(self) -> dict[str, Any]:
        return {
            "enable_rename": self.enable_rename.get(),
            "review_before_apply": self.setup_review.get(),
            "filename_date_style": self.filename_date_style.get(),
            "rename_folder_date": self.rename_folder_date.get(),
            "auto_move_working": self.auto_move_working.get(),
            "auto_advance_images": self.auto_advance_images.get(),
            "csv_mode": self.csv_mode.get(),
        }

    def save_setup_defaults(self) -> None:
        settings = self._setup_settings_value()
        result = self._run(lambda: save_last("project_setup", settings))
        if result:
            if self.workflow is not None:
                self._run(lambda: self.workflow.save_project_settings(settings))
            self.status.set("Saved project-setup choices as the automatic defaults.")

    def _session_for_folder(self, folder: Path, model: dict[str, Any]) -> str:
        names = [item.name for item in loose_image_files(folder)]
        match = match_experiment_folder(folder, model, image_names=names)
        if match.status == "MATCHED" and match.session_uid:
            return match.session_uid
        if match.status == "AMBIGUOUS":
            value = simpledialog.askstring(
                "Choose V10 session",
                f"Folder: {folder.name}\n\nCandidates:\n" + "\n".join(match.candidates) + "\n\nEnter the correct sessionUID:",
                parent=self,
            )
            if value in match.candidates:
                return str(value)
            raise ValueError(f"No valid V10 session was selected for {folder.name}.")
        raise ValueError(
            f"Could not match {folder.name!r} to V10 ({match.status}). Add a supported date to the folder name or use Create from V10 and connect it manually."
        )

    def _open_or_create_folder(
        self, folder: Path, workbook: Path, model: dict[str, Any]
    ) -> ProjectWorkflow:
        try:
            return ProjectWorkflow.open(folder)
        except ValueError as exc:
            if "Project state not found" not in str(exc):
                raise
        session_uid = self._session_for_folder(folder, model)
        return ProjectWorkflow.create_from_model(
            subset_project_model(model, session_uid),
            folder,
            v10_workbook=workbook,
        )

    def _prepare_workflow(self, workflow: ProjectWorkflow, *, confirmed: bool = False) -> dict[str, Any]:
        settings = self._setup_settings_value()
        migration = workflow.preview_layout_migration()
        loose = workflow.preview_loose_import()
        if loose.get("blockers") or migration.get("blockers"):
            raise ValueError("Setup has folder/file collisions; review the Setup details before applying.")
        needs_confirmation = not confirmed and (self.setup_review.get() or bool(migration.get("moves")))
        if needs_confirmation and not messagebox.askyesno(
            "Prepare experiment project",
            f"Project: {workflow.project_root.name}\n\n"
            f"Legacy folder moves: {len(migration.get('moves', []))}\n"
            f"Loose images to move into Raw: {sum(item['status'] == 'WOULD_MOVE' for item in loose.get('items', []))}\n"
            f"Expected V10 images: {len(workflow.state['images'])}\n\n"
            "Apply these safe, non-overwriting changes?",
            parent=self,
        ):
            raise RuntimeError("Project preparation was cancelled.")
        if migration.get("moves"):
            workflow.apply_layout_migration(migration)
            loose = workflow.preview_loose_import()
        if any(item["status"] == "WOULD_MOVE" for item in loose.get("items", [])):
            workflow.apply_loose_import(loose)
        workflow.save_project_settings(settings)
        result = workflow.apply_setup(
            enable_rename=self.enable_rename.get(),
            filename_date_style=self.filename_date_style.get(),
        )
        if self.rename_folder_date.get():
            workflow.rename_project_date("yyyy.mm.dd")
        workflow.auto_attach_grids()
        save_last("project_setup", settings)
        return result

    def prepare_one_folder(self) -> None:
        workbook = filedialog.askopenfilename(
            title="Select V10 workbook",
            filetypes=[("Excel workbook", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if not workbook:
            return
        folder = filedialog.askdirectory(title="Select one experiment folder")
        if not folder:
            return
        def action() -> tuple[ProjectWorkflow, dict[str, Any]]:
            model = load_v10(workbook)
            selected = Path(folder)
            try:
                workflow = ProjectWorkflow.open(selected)
            except ValueError as exc:
                if "Project state not found" not in str(exc):
                    raise
                session_uid = self._session_for_folder(selected, model)
                migration = plan_layout_migration(selected)
                loose = plan_loose_image_import(selected)
                if (self.setup_review.get() or migration.get("moves")) and not messagebox.askyesno(
                    "Prepare experiment project",
                    f"Project: {selected.name}\n\n"
                    f"Legacy folder moves: {len(migration.get('moves', []))}\n"
                    f"Loose images to move into Raw: {sum(item['status'] == 'WOULD_MOVE' for item in loose.get('items', []))}\n"
                    f"Expected V10 images: {len(subset_project_model(model, session_uid)['images'])}\n\n"
                    "Apply these safe, non-overwriting changes?",
                    parent=self,
                ):
                    raise RuntimeError("Project preparation was cancelled.")
                workflow = ProjectWorkflow.create_from_model(
                    subset_project_model(model, session_uid),
                    selected,
                    v10_workbook=workbook,
                )
                return workflow, self._prepare_workflow(workflow, confirmed=True)
            return workflow, self._prepare_workflow(workflow)
        prepared = self._run(action)
        if prepared:
            workflow, result = prepared
            self._activate(workflow)
            self._show_setup_result(result)
            self.status.set(f"Prepared/resumed {workflow.project_root.name}; CSV snapshot: {result.get('csv_snapshot', {}).get('status', 'unknown')}.")

    def prepare_parent_folder(self) -> None:
        workbook = filedialog.askopenfilename(
            title="Select V10 workbook",
            filetypes=[("Excel workbook", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if not workbook:
            return
        parent = filedialog.askdirectory(title="Select parent of experiment folders")
        if not parent:
            return
        def action() -> tuple[list[ProjectWorkflow], list[str]]:
            model = load_v10(workbook)
            folders = discover_experiment_folders(parent)
            if not folders:
                raise ValueError("No experiment subfolders with loose images or project state were found.")
            pending: list[tuple[Path, ProjectWorkflow | None, str | None]] = []
            summaries: list[str] = []
            for folder in folders:
                try:
                    pending.append((folder, ProjectWorkflow.open(folder), None))
                except ValueError as exc:
                    if "Project state not found" not in str(exc):
                        raise
                    pending.append((folder, None, self._session_for_folder(folder, model)))
            migrations = sum(
                len(plan_layout_migration(folder).get("moves", []))
                for folder, _workflow, _session_uid in pending
            )
            loose_count = sum(
                sum(
                    entry["status"] == "WOULD_MOVE"
                    for entry in plan_loose_image_import(folder).get("items", [])
                )
                for folder, _workflow, _session_uid in pending
            )
            if (self.setup_review.get() or migrations) and not messagebox.askyesno(
                "Prepare parent projects",
                f"Experiment projects: {len(pending)}\nLegacy folder moves: {migrations}\nLoose images to move into Raw: {loose_count}\n\nApply the complete parent-folder plan?",
                parent=self,
            ):
                raise RuntimeError("Parent project preparation was cancelled.")
            workflows: list[ProjectWorkflow] = []
            for folder, workflow, session_uid in pending:
                if workflow is None:
                    if session_uid is None:
                        raise RuntimeError("Missing planned V10 session assignment.")
                    workflow = ProjectWorkflow.create_from_model(
                        subset_project_model(model, session_uid),
                        folder,
                        v10_workbook=workbook,
                    )
                workflows.append(workflow)
                result = self._prepare_workflow(workflow, confirmed=True)
                summaries.append(f"{workflow.project_root.name}: {result['summary']['copied_count']} Working copies")
            return workflows, summaries
        prepared = self._run(action)
        if prepared:
            workflows, summaries = prepared
            self._activate(workflows[-1])
            messagebox.showinfo("Parent preparation complete", "\n".join(summaries), parent=self)
            self.status.set(f"Prepared/resumed {len(workflows)} independent experiment projects.")

    def open_project(self) -> None:
        root = filedialog.askdirectory(title="Select the project root folder")
        if not root:
            return
        workflow = self._run(lambda: ProjectWorkflow.open(root))
        if workflow:
            self._activate(workflow)

    def _activate(self, workflow: ProjectWorkflow) -> None:
        self.workflow = workflow
        project_settings = workflow.state.get("settings", {})
        if isinstance(project_settings, dict) and project_settings:
            self.enable_rename.set(bool(project_settings.get("enable_rename", self.enable_rename.get())))
            self.setup_review.set(bool(project_settings.get("review_before_apply", self.setup_review.get())))
            self.filename_date_style.set(str(project_settings.get("filename_date_style", self.filename_date_style.get())))
            self.rename_folder_date.set(bool(project_settings.get("rename_folder_date", self.rename_folder_date.get())))
            self.auto_move_working.set(bool(project_settings.get("auto_move_working", self.auto_move_working.get())))
            self.auto_advance_images.set(
                bool(
                    project_settings.get(
                        "auto_advance_images", self.auto_advance_images.get()
                    )
                )
            )
            self.csv_mode.set(str(project_settings.get("csv_mode", self.csv_mode.get())))
        self.raw_root_var.set(str(preferred_project_path(workflow.project_root, "raw")))
        self._run(workflow.auto_attach_grids)
        values = list(workflow.state["images"])
        self.image_picker.configure(values=values)
        if values:
            self.image_uid.set(values[0])
            self._refresh_asset_labels()
            try:
                source = workflow.source_for(values[0])
            except FileNotFoundError:
                self.status.set(
                    "Project opened. Preview and apply Setup to connect expected images."
                )
            else:
                with Image.open(source) as image:
                    self.viewer.show(image)
                self.status.set(f"Opened project: {workflow.project_root}")
        else:
            self.status.set(f"Opened project: {workflow.project_root}")
        self.refresh_batch_images()

    def _selected(self) -> tuple[ProjectWorkflow, str]:
        if self.workflow is None:
            raise ValueError("Create or open a project first.")
        uid = self.image_uid.get().strip()
        if not uid:
            raise ValueError("Select an Image UID.")
        return self.workflow, uid

    def load_selected_source(self, _event: object | None = None) -> None:
        def action() -> None:
            workflow, uid = self._selected()
            self.crop_export_plan = None
            self.crop_export_signature = None
            source = workflow.source_for(uid)
            with Image.open(source) as image:
                self.viewer.show(image)
            self.viewer.set_handlers()
            self._refresh_asset_labels()
            self.status.set(f"Loaded {uid}: {source}")

        self._run(action)

    def choose_raw_root(self) -> None:
        directory = filedialog.askdirectory(title="Select project Raw root")
        if directory:
            self.raw_root_var.set(directory)
            self.setup_preview = None
            self.setup_signature = None

    def _setup_signature_value(self) -> tuple[str, bool, str]:
        raw = self.raw_root_var.get().strip()
        if not raw:
            workflow, _uid = self._selected()
            raw = str(preferred_project_path(workflow.project_root, "raw"))
            self.raw_root_var.set(raw)
        return str(Path(raw).resolve()), self.enable_rename.get(), self.filename_date_style.get()

    def _show_setup_result(self, result: dict[str, Any]) -> None:
        for item in self.setup_tree.get_children():
            self.setup_tree.delete(item)
        for image in result["images"]:
            self.setup_tree.insert(
                "",
                "end",
                values=(
                    image["raw_path"],
                    image["image_uid"],
                    image["working_path"],
                    image["disposition"],
                ),
            )
        summary = result["summary"]
        self.status.set(
            "Setup preview: "
            f"{summary['ready_to_copy_count']} ready, "
            f"{summary['unchanged_current_count']} current, "
            f"{summary['expected_not_present_count']} expected missing, "
            f"{summary['ambiguous_source_count']} ambiguous, "
            f"{summary['target_collision_count']} collisions."
        )

    def preview_project_setup(self) -> None:
        workflow, _uid = self._selected()
        signature = self._setup_signature_value()
        result = self._run(
            lambda: workflow.preview_setup(
                raw_root=signature[0], enable_rename=signature[1], filename_date_style=signature[2]
            )
        )
        if result:
            self.setup_preview = result
            self.setup_signature = signature
            self._show_setup_result(result)

    def apply_project_setup(self) -> None:
        workflow, _uid = self._selected()
        signature = self._setup_signature_value()
        if self.setup_preview is None or self.setup_signature != signature:
            messagebox.showerror(
                "Project setup", "Preview the current Raw root and rename choice first."
            )
            return
        summary = self.setup_preview["summary"]
        if self.setup_review.get() and not messagebox.askyesno(
            "Apply project setup",
            "Create only the previewed non-conflicting Working copies?\n\n"
            f"Ready: {summary['ready_to_copy_count']}\n"
            f"Expected missing: {summary['expected_not_present_count']}\n"
            f"Ambiguous/collisions: "
            f"{summary['ambiguous_source_count'] + summary['target_collision_count']}",
        ):
            return
        result = self._run(
            lambda: workflow.apply_setup(
                raw_root=signature[0], enable_rename=signature[1], filename_date_style=signature[2]
            )
        )
        if result:
            settings = self._setup_settings_value()
            workflow.save_project_settings(settings)
            save_last("project_setup", settings)
            if self.rename_folder_date.get():
                workflow.rename_project_date("yyyy.mm.dd")
                self._activate(workflow)
            self.setup_preview = None
            self.setup_signature = None
            self._show_setup_result(result)
            self.status.set(
                f"Setup applied: {result['summary']['copied_count']} copied; "
                "project state and conversion audit map saved."
            )
            self.load_selected_source()

    def migrate_project_layout(self) -> None:
        workflow, _uid = self._selected()
        plan = self._run(workflow.preview_layout_migration)
        if not plan:
            return
        if not plan.get("moves"):
            self.status.set("Project already uses the numbered folder layout.")
            return
        if plan.get("blockers"):
            messagebox.showerror("Folder migration", "Folder migration has conflicting destinations.", parent=self)
            return
        if not messagebox.askyesno("Upgrade project folders", f"Move/merge {len(plan['moves'])} legacy folder location(s) into the numbered layout?", parent=self):
            return
        result = self._run(lambda: workflow.apply_layout_migration(plan))
        if result:
            self._activate(workflow)
            self.status.set("Project folders upgraded to the numbered layout.")

    def mark_working_complete(self) -> None:
        workflow, _uid = self._selected()
        if not messagebox.askyesno("Mark Working complete", "Move and canonicalise Working beneath 2. Cropped without inventing crop results?", parent=self):
            return
        result = self._run(workflow.mark_working_complete)
        if result:
            self.status.set(f"Working completion: {result['status']} — {result['path']}")

    def rename_project_date_now(self) -> None:
        workflow, _uid = self._selected()
        result = self._run(lambda: workflow.rename_project_date("yyyy.mm.dd"))
        if result:
            self._activate(workflow)
            self.status.set(f"Project folder date is sortable: {workflow.project_root.name}")

    def refresh_v10_csvs(self) -> None:
        workflow, _uid = self._selected()
        result = self._run(lambda: workflow.refresh_from_v10(filename_date_style=self.filename_date_style.get()))
        if result:
            self.csv_mode.set("refreshable")
            settings = self._setup_settings_value()
            workflow.save_project_settings(settings)
            save_last("project_setup", settings)
            self._activate(workflow)
            self.status.set(f"Refreshed V10 and active CSV snapshot: {result['status']} {result.get('snapshot_id', '')}")

    def keep_current_csvs(self) -> None:
        workflow, _uid = self._selected()
        self.csv_mode.set("pinned")
        settings = self._setup_settings_value()
        result = self._run(
            lambda: workflow.refresh_csv_snapshot(
                filename_date_style=self.filename_date_style.get(), pinned=True
            )
        )
        if result:
            workflow.save_project_settings(settings)
            save_last("project_setup", settings)
            self.status.set(
                f"Keeping CSV snapshot {result.get('snapshot_id', '')}; use Refresh V10 to regenerate."
            )

    def compare_v10_csvs(self) -> None:
        workflow, _uid = self._selected()
        result = self._run(lambda: workflow.compare_current_v10(filename_date_style=self.filename_date_style.get()))
        if result:
            messagebox.showinfo("V10 comparison", f"Current exported CSVs versus V10: {result['status']}", parent=self)

    def auto_attach_grids(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, _uid = selected
        result = self._run(workflow.auto_attach_grids)
        if result is not None:
            self._refresh_asset_labels()
            self.status.set(
                f"Grid search: {len(result['attached'])} attached, "
                f"{len(result['ambiguous'])} ambiguous, {len(result['missing'])} not found."
            )

    def preview_grid_discovery(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, _uid = selected
        result = self._run(workflow.preview_grid_discovery)
        if result is not None:
            self.status.set(
                f"Grid preview only: {len(result['unique'])} unique, "
                f"{len(result['ambiguous'])} ambiguous, {len(result['missing'])} missing; "
                "project state is unchanged."
            )

    def start_orientation(self) -> None:
        def action() -> None:
            workflow, uid = self._selected()
            source = workflow.orientation_source_for(uid)
            with Image.open(source) as image:
                self.viewer.show(image)
            self.orientation_proposal = None
            self.orientation_points = []
            settings = {
                "input_mode": self.orientation_input_mode.get(),
                "auto_preview": self.orientation_auto_preview.get(),
            }
            save_last("orientation", settings)
            if self.orientation_input_mode.get() == "two_points":
                self.viewer.set_handlers(click=self._orientation_point_clicked)
                self.status.set(
                    "Click the first point, then the second point on the edge that should be horizontal."
                )
            else:
                self.viewer.set_handlers(drag=self._orientation_dragged)
                self.status.set(
                    "Drag a line from left to right along the edge that should be horizontal."
                )

        self._run(action)

    def _orientation_dragged(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> None:
        self._propose_orientation_points(start, end)

    def _orientation_point_clicked(self, point: tuple[float, float]) -> None:
        self.orientation_points.append(point)
        self.viewer.draw_points(self.orientation_points)
        if len(self.orientation_points) == 1:
            self.status.set("First alignment point recorded; click the second point.")
            return
        self.viewer.set_handlers()
        self._propose_orientation_points(
            self.orientation_points[0], self.orientation_points[1]
        )

    def _propose_orientation_points(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> None:
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.propose_orientation(uid, (*start, *end)))
        if result:
            self.orientation_proposal, _preview = result
            line = self.orientation_proposal["diagnostics"]["line"]
            if self.orientation_input_mode.get() == "line":
                self.viewer.draw_line(
                    (line["x1"], line["y1"]), (line["x2"], line["y2"])
                )
            self.status.set(
                f"Proposed correction: {self.orientation_proposal['angle_degrees']:.4f}°. Preview before accepting."
            )
            if self.orientation_auto_preview.get():
                self.preview_orientation()

    def preview_orientation(self) -> None:
        if self.orientation_proposal is None:
            messagebox.showerror("Orientation", "Drag an edge line first.")
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.propose_orientation(
                uid,
                tuple(
                    self.orientation_proposal["diagnostics"]["line"][key]
                    for key in ("x1", "y1", "x2", "y2")
                ),
            )
        )
        if result:
            self.orientation_proposal, preview = result
            self.viewer.show(preview)
            self.status.set(
                "Orientation preview only; source and project state are unchanged."
            )

    def accept_orientation(self) -> None:
        if self.orientation_proposal is None:
            messagebox.showerror("Orientation", "Preview an orientation first.")
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.accept_orientation(uid, self.orientation_proposal)
        )
        if result:
            _accepted, output = result
            self.status.set(f"Accepted orientation: {output}")
            self.orientation_proposal = None
            self._advance_after_stage(uid, "orientation")

    def skip_orientation(self) -> None:
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.propose_orientation(uid, None, skip=True))
        if result:
            proposal, _preview = result
            accepted = self._run(lambda: workflow.accept_orientation(uid, proposal))
            if accepted:
                self.status.set(
                    "Orientation skipped; downstream routes remain available."
                )
                self.orientation_proposal = None
                self._advance_after_stage(uid, "orientation")

    def start_calibration(self) -> None:
        def action() -> None:
            workflow, uid = self._selected()
            source = workflow.source_for(uid, include_crop=False)
            with Image.open(source) as image:
                self.viewer.show(image)
                self.calibration_source_dimensions = image.size
            self.calibration_points = []
            self.calibration_proposal = None
            self.viewer.set_handlers(click=self._calibration_clicked)
            self.status.set(
                "Click useful boundaries in order: left, right, top, bottom. "
                "Coordinates are converted to original-image pixels."
            )

        self._run(action)

    def _calibration_clicked(self, point: tuple[float, float]) -> None:
        self.calibration_points.append(point)
        self.viewer.draw_points(self.calibration_points)
        labels = ("left", "right", "top", "bottom")
        if len(self.calibration_points) < 4:
            self.status.set(
                f"Recorded {labels[len(self.calibration_points) - 1]}; click {labels[len(self.calibration_points)]}."
            )
            return
        self.viewer.set_handlers()
        options = self._crop_calibration_options()
        self.calibration_proposal = self._run(
            lambda: calibrate_crop_size(
                *self.calibration_points,
                **options,
                source_dimensions=self.calibration_source_dimensions,
            )
        )
        if self.calibration_proposal:
            side = self.calibration_proposal["side_pixels"]
            measured = self.calibration_proposal["measured_extents"]
            source = self.calibration_source_dimensions or ("?", "?")
            client = self.viewer.coordinate_client_dimensions
            self.calibration_label.configure(
                text=(
                    f"Source {source[0]}×{source[1]} px; measured "
                    f"{measured['measured_width']:.0f}×{measured['measured_height']:.0f}; "
                    f"proposed {side}×{side} px; {self.viewer.coordinate_source} "
                    f"{client[0]}×{client[1]}"
                )
            )
            self.status.set(
                "Review the proposed reusable size, then accept or recalibrate."
            )

    def accept_calibration(self) -> None:
        if len(self.calibration_points) != 4 or self.calibration_proposal is None:
            messagebox.showerror(
                "Crop calibration", "Collect four valid boundary clicks first."
            )
            return
        calibration_id = simpledialog.askstring(
            "Crop calibration", "Calibration name", initialvalue="plate-default"
        )
        if not calibration_id:
            return
        workflow, _uid = self._selected()
        options = self._crop_calibration_options()
        result = self._run(
            lambda: workflow.accept_crop_calibration(
                *self.calibration_points,
                calibration_id=calibration_id,
                **options,
                source_dimensions=self.calibration_source_dimensions,
            )
        )
        if result:
            self._refresh_crop_calibration_presets(calibration_id)
            self.calibration_label.configure(
                text=f"Accepted {calibration_id}: {result['side_pixels']} × {result['side_pixels']} px"
            )
            self.status.set(
                "Crop size accepted and reusable; placement remains per image."
            )

    def accept_exact_calibration(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, uid = selected
        try:
            side = int(self.crop_exact_side.get().strip())
        except ValueError:
            messagebox.showerror(
                "Crop calibration", "Enter a positive whole-pixel exact final side."
            )
            return
        source = self._run(lambda: workflow.source_for(uid, include_crop=False))
        if source is None:
            return
        with Image.open(source) as image:
            dimensions = image.size
        calibration_id = simpledialog.askstring(
            "Crop calibration",
            "Exact-size calibration name",
            initialvalue="plate-exact",
        )
        if not calibration_id:
            return
        result = self._run(
            lambda: workflow.accept_exact_crop_calibration(
                side,
                calibration_id=calibration_id,
                source_dimensions=dimensions,
            )
        )
        if result:
            settings = load_last("plate_crop", {}) or {}
            settings["exact_side_pixels"] = side
            settings["auto_preview"] = self.crop_auto_preview.get()
            settings["calibration_id"] = calibration_id
            save_last("plate_crop", settings)
            self._refresh_crop_calibration_presets(calibration_id)
            self.calibration_label.configure(
                text=f"Accepted exact {calibration_id}: {side} × {side} px"
            )
            self.status.set(
                "Exact reusable crop size accepted; no calibration clicks were used."
            )

    def _crop_calibration_options(self) -> dict[str, Any]:
        increment = int(self.crop_rounding_increment.get())
        margin = float(self.crop_margin_value.get())
        if increment < 1:
            raise ValueError("Crop rounding increment must be a positive integer.")
        if margin < 0:
            raise ValueError("Crop margin cannot be negative.")
        options = {
            "rounding_enabled": self.crop_rounding_enabled.get(),
            "increment": increment,
            "rounding_direction": self.crop_rounding_direction.get(),
            "margin_value": margin,
            "margin_unit": self.crop_margin_unit.get(),
        }
        save_last(
            "plate_crop",
            {
                **options,
                "rounding_increment": increment,
                "auto_preview": self.crop_auto_preview.get(),
            },
        )
        return options

    def _current_calibration_id(self) -> str:
        workflow, _uid = self._selected()
        calibrations = workflow.state["crop_calibrations"]
        if not calibrations:
            raise ValueError("Accept a crop-size calibration first.")
        calibration_id = self.crop_calibration_id.get().strip()
        if calibration_id not in calibrations:
            raise ValueError("Select a saved crop-size preset first.")
        return calibration_id

    def _crop_calibration_selected(self, _event: tk.Event | None = None) -> None:
        self._apply_crop_calibration_selection(self.crop_calibration_id.get())

    def _apply_crop_calibration_selection(self, calibration_id: str) -> None:
        if self.workflow is None:
            return
        calibration = self.workflow.state.get("crop_calibrations", {}).get(
            calibration_id
        )
        if not isinstance(calibration, dict):
            return
        self.crop_rounding_enabled.set(
            bool(calibration.get("rounding_enabled", True))
        )
        self.crop_rounding_increment.set(
            str(calibration.get("rounding_increment", 50))
        )
        self.crop_rounding_direction.set(
            str(calibration.get("rounding_direction", "down"))
        )
        self.crop_margin_value.set(str(calibration.get("margin_value", 0)))
        self.crop_margin_unit.set(str(calibration.get("margin_unit", "pixels")))
        if calibration.get("method") == "manual_exact_final_side_pixels":
            self.crop_exact_side.set(str(calibration["side_pixels"]))
        self.calibration_label.configure(
            text=(
                f"Selected {calibration_id}: {calibration['side_pixels']} × "
                f"{calibration['side_pixels']} px"
            )
        )
        settings = load_last("plate_crop", {}) or {}
        settings["calibration_id"] = calibration_id
        save_last("plate_crop", settings)
        self._run(lambda: self.workflow.select_crop_calibration(calibration_id))
        self.status.set(f"Using saved crop-size preset: {calibration_id}.")

    def _refresh_crop_calibration_presets(self, select: str | None = None) -> None:
        if self.workflow is None:
            return
        calibrations = self.workflow.state.get("crop_calibrations", {})
        values = list(calibrations)
        self.crop_calibration_box.configure(values=values)
        desired = (
            select
            or self.workflow.state.get("active_crop_calibration_id")
            or self.crop_calibration_id.get()
        )
        if desired not in calibrations:
            desired = values[-1] if values else ""
        self.crop_calibration_id.set(desired)
        if desired:
            self._apply_crop_calibration_selection(desired)

    def start_crop_placement(self) -> None:
        settings = load_last("plate_crop", {}) or {}
        settings["auto_preview"] = self.crop_auto_preview.get()
        save_last("plate_crop", settings)

        def action() -> None:
            workflow, uid = self._selected()
            self._current_calibration_id()
            source = workflow.source_for(uid, include_crop=False)
            with Image.open(source) as image:
                self.viewer.show(image)
            self.crop_points = []
            self.crop_proposal = None
            self.crop_previewed = False
            self.viewer.set_handlers(click=self._crop_clicked)
            self.status.set("Click the left useful edge, then the top useful edge.")

        self._run(action)

    def _crop_clicked(self, point: tuple[float, float]) -> None:
        self.crop_points.append(point)
        self.viewer.draw_points(self.crop_points)
        if len(self.crop_points) == 1:
            self.status.set("Left edge recorded; click the top edge.")
            return
        self.viewer.set_handlers()
        workflow, uid = self._selected()
        calibration_id = self._current_calibration_id()
        result = self._run(
            lambda: workflow.propose_crop(
                uid, calibration_id, self.crop_points[0], self.crop_points[1]
            )
        )
        if result:
            self.crop_proposal, _preview = result
            self.viewer.draw_box(self.crop_proposal["crop_box"])
            self.status.set(
                "Crop overlay proposed. Preview the cropped image before accepting."
            )
            if self.crop_auto_preview.get():
                self.preview_crop()

    def preview_crop(self) -> None:
        if self.crop_proposal is None:
            messagebox.showerror("Plate crop", "Place a crop first.")
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.propose_crop(
                uid,
                self.crop_proposal["calibration_id"],
                self.crop_points[0],
                self.crop_points[1],
            )
        )
        if result:
            self.crop_proposal, preview = result
            self.crop_previewed = True
            self.viewer.show(preview)
            self.status.set(
                "Crop preview only; source and project state are unchanged."
            )

    def accept_crop(self) -> None:
        if self.crop_proposal is None or not self.crop_previewed:
            messagebox.showerror(
                "Plate crop", "Preview the proposed crop before accepting."
            )
            return
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.accept_crop(uid, self.crop_proposal))
        if result:
            _accepted, output = result
            self.status.set(f"Accepted plate crop: {output}")
            self.crop_proposal = None
            self._advance_after_stage(uid, "crop")

    def skip_crop(self) -> None:
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.skip_crop(uid))
        if result:
            self.crop_proposal = None
            self.status.set(
                "Plate crop skipped; the existing four-point route remains available."
            )
            self._advance_after_stage(uid, "crop")

    def attach_grid(self) -> None:
        path = filedialog.askopenfilename(
            title="Select accepted grid coordinate asset",
            filetypes=[("Grid asset", "*.grid.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        workflow, uid = self._selected()
        asset = self._run(lambda: workflow.attach_grid_asset(uid, path))
        if asset:
            self._refresh_asset_labels()
            self.status.set(
                f"Attached {asset['asset_id']} with {len(asset['spots'])} reusable spot coordinates."
            )
            self._advance_after_stage(uid, "grid")

    def skip_current_grid(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, uid = selected
        result = self._run(lambda: workflow.skip_grid(uid))
        if result:
            self.status.set("Grid attachment skipped for this image.")
            self._advance_after_stage(uid, "grid")

    @staticmethod
    def _parse_crop_columns(text: str) -> tuple[int, ...] | None:
        value = text.strip()
        if not value:
            return None
        columns: list[int] = []
        for part in value.split(","):
            token = part.strip()
            if not token:
                raise ValueError("Crop columns contain an empty item.")
            if "-" in token:
                pieces = token.split("-", 1)
                start, end = int(pieces[0]), int(pieces[1])
                if start > end:
                    raise ValueError("Crop column ranges must increase.")
                wanted = range(start, end + 1)
            else:
                wanted = (int(token),)
            for column in wanted:
                if column < 1:
                    raise ValueError("Crop columns must be positive.")
                if column not in columns:
                    columns.append(column)
        return tuple(columns)

    def _culture_crop_settings(self) -> dict[str, Any]:
        width, height = int(self.crop_export_width.get()), int(self.crop_export_height.get())
        if width < 1 or height < 1:
            raise ValueError("Crop width and height must be positive integers.")
        source_kind = self.crop_export_source.get()
        tier = "Processed" if source_kind.casefold() == "processed" else "Unprocessed"
        self.crop_export_tier.set(tier)
        return {
            "width": width,
            "height": height,
            "tier": tier,
            "source_kind": source_kind,
            "top": self.crop_export_top.get(),
            "low": self.crop_export_low.get(),
            "columns": self.crop_export_columns.get().strip(),
        }

    def calculate_culture_crop_size(self) -> None:
        result = self._run(lambda: calculate_box_from_roi(*(float(value.get()) for value in self.crop_export_roi)))
        if result:
            self.crop_export_width.set(str(result["width"]))
            self.crop_export_height.set(str(result["height"]))
            save_last("culture_crop", self._culture_crop_settings())
            self.status.set(f"Calculated reusable culture crop: {result['width']} × {result['height']} px.")

    def save_culture_crop_preset(self) -> None:
        settings = self._run(self._culture_crop_settings)
        if settings is None:
            return
        name = simpledialog.askstring("Culture crop preset", "Preset name:", parent=self)
        if name:
            self._run(lambda: save_preset("culture_crop", name, settings))
            self.crop_export_preset_box.configure(values=list_presets("culture_crop"))
            self.crop_export_preset.set(name)
            save_last("culture_crop", settings)

    def load_culture_crop_preset(self) -> None:
        if not self.crop_export_preset.get():
            return
        settings = self._run(lambda: load_preset("culture_crop", self.crop_export_preset.get()))
        if settings:
            self.crop_export_width.set(str(settings["width"]))
            self.crop_export_height.set(str(settings["height"]))
            self.crop_export_tier.set(str(settings.get("tier", self.crop_export_tier.get())))
            self.crop_export_source.set(str(settings.get("source_kind", self.crop_export_source.get())))
            self.crop_export_top.set(bool(settings.get("top", self.crop_export_top.get())))
            self.crop_export_low.set(bool(settings.get("low", self.crop_export_low.get())))
            self.crop_export_columns.set(str(settings.get("columns", self.crop_export_columns.get())))
            save_last("culture_crop", settings)

    def _crop_export_signature_value(self) -> tuple[Any, ...]:
        _workflow, uid = self._selected()
        states = tuple(
            state
            for state, enabled in (
                ("Top", self.crop_export_top.get()),
                ("Low", self.crop_export_low.get()),
            )
            if enabled
        )
        if not states:
            raise ValueError("Select Top and/or Low culture crops.")
        columns = self._parse_crop_columns(self.crop_export_columns.get())
        width = int(self.crop_export_width.get())
        height = int(self.crop_export_height.get())
        if width < 1 or height < 1:
            raise ValueError("Crop width and height must be positive integers.")
        save_last("culture_crop", self._culture_crop_settings())
        source_kind = self.crop_export_source.get()
        tier = "Processed" if source_kind.casefold() == "processed" else "Unprocessed"
        self.crop_export_tier.set(tier)
        return (
            uid,
            tier,
            source_kind,
            states,
            columns,
            width,
            height,
        )

    def preview_culture_crop_export(self) -> None:
        workflow, _uid = self._selected()
        signature = self._run(self._crop_export_signature_value)
        if signature is None:
            return
        uid, tier, source_kind, states, columns, width, height = signature
        plan = self._run(
            lambda: workflow.preview_culture_crop_export(
                uid,
                tier=tier,
                states=states,
                columns=columns,
                crop_width=width,
                crop_height=height,
                source_kind=source_kind,
            )
        )
        if not plan:
            return
        self.crop_export_plan = plan
        self.crop_export_signature = signature
        for item in self.crop_export_tree.get_children():
            self.crop_export_tree.delete(item)
        for crop in plan["crops"]:
            box = crop["rectangle"]
            self.crop_export_tree.insert(
                "",
                "end",
                values=(
                    crop["state"],
                    crop["column"],
                    crop["strain_label"],
                    f"{box['left']},{box['top']} {box['width']}×{box['height']}",
                ),
            )
        disposition = (
            "already current" if plan["status"] == "UNCHANGED_CURRENT" else "new"
        )
        self.status.set(
            f"Validated {len(plan['crops'])} {tier} crops ({disposition}); "
            "no files were written."
        )

    def accept_culture_crop_export(self) -> None:
        workflow, _uid = self._selected()
        signature = self._run(self._crop_export_signature_value)
        if signature is None:
            return
        if self.crop_export_plan is None or self.crop_export_signature != signature:
            messagebox.showerror(
                "Culture crops",
                "Preview the current image, tier, states, columns and dimensions first.",
            )
            return
        plan = self.crop_export_plan
        if not messagebox.askyesno(
            "Export culture crops",
            f"Publish {len(plan['crops'])} validated crops to:\n\n"
            f"{plan['output_directory']}?",
        ):
            return
        result = self._run(
            lambda: workflow.accept_culture_crop_export(signature[0], plan)
        )
        if result:
            self.crop_export_plan = None
            self.crop_export_signature = None
            self.status.set(
                f"Accepted {len(result['crops'])} {result['tier']} crops: "
                f"{result['output_directory']}"
            )
            self._advance_after_stage(signature[0], "culture")

    def skip_culture_crop_export(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        _workflow, uid = selected
        self.crop_export_plan = None
        self.crop_export_signature = None
        self.status.set("Culture-crop export skipped for this pass.")
        self._advance_after_stage(uid, "culture")

    def preview_visibility(self) -> None:
        workflow, uid = self._selected()
        save_last("visibility", {"preset": self.visibility_preset.get()})
        result = self._run(
            lambda: workflow.propose_visibility(uid, self.visibility_preset.get())
        )
        if result:
            self.visibility_proposal, preview = result
            self.viewer.show(preview)
            parameters = self.visibility_proposal["parameters"]
            self.status.set(
                "Visibility preview only: "
                f"black={parameters['black_point']}, "
                f"white={parameters['white_point']}, gamma={parameters['gamma']}."
            )

    def accept_visibility(self) -> None:
        if self.visibility_proposal is None:
            messagebox.showerror("Visibility", "Preview an adjustment first.")
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.accept_visibility(uid, self.visibility_proposal)
        )
        if result:
            _accepted, output, sidecar = result
            self.visibility_proposal = None
            self.status.set(
                f"Accepted visibility derivative: {output}\nRecord: {sidecar}"
            )
            self._advance_after_stage(uid, "visibility")

    def flag_visibility(self) -> None:
        if self.visibility_proposal is None:
            messagebox.showerror("Visibility", "Preview an adjustment first.")
            return
        reason = simpledialog.askstring(
            "Manual visibility review",
            "Reason / manual action needed",
            initialvalue="Preset needs manual adjustment",
        )
        if reason is None:
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.flag_visibility_review(
                uid, self.visibility_proposal, reason
            )
        )
        if result:
            self.visibility_proposal = None
            self.status.set("Visibility flagged in project state for manual review.")
            self._advance_after_stage(uid, "visibility")

    def skip_visibility(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, uid = selected
        result = self._run(lambda: workflow.skip_derivative(uid, "visibility"))
        if result:
            self.visibility_proposal = None
            self.status.set("Visibility skipped for this image.")
            self._advance_after_stage(uid, "visibility")

    def _annotation_request(self) -> dict[str, Any]:
        workflow, uid = self._selected()
        request = workflow.default_annotation_request(uid)
        request["labels"] = {
            key: variable.get().strip()
            for key, variable in self.annotation_labels.items()
            if variable.get().strip()
        }
        return request

    def _annotation_preset(self) -> dict[str, Any]:
        strain_size = int(self.annotation_strain_size.get())
        vertical_size = int(self.annotation_vertical_size.get())
        rotation = float(self.annotation_rotation.get())
        if strain_size < 1 or vertical_size < 1:
            raise ValueError("Annotation font sizes must be positive integers.")
        preset = {
            **self.annotation_preset_settings,
            "name": "user_preview",
            "strain_font_size": strain_size,
            "vertical_font_size": vertical_size,
            "strain_rotation_degrees": rotation,
            "source_kind": self.annotation_source.get(),
            "header_enabled": self.annotation_header_enabled.get(),
            "header_grouped": self.annotation_header_grouped.get(),
            "in_image_enabled": self.annotation_in_image_enabled.get(),
            "in_image_grouped": self.annotation_in_image_grouped.get(),
            "header_field_visibility": {key: value.get() for key, value in self.annotation_label_enabled.items()},
            "in_image_field_visibility": {
                **{key: value.get() for key, value in self.annotation_label_enabled.items()},
                **self.annotation_preset_settings.get("in_image_field_visibility", {}),
            },
        }
        save_last("annotation", preset)
        return preset

    def _sync_annotation_controls(self) -> None:
        settings = self.annotation_preset_settings
        self.annotation_header_enabled.set(bool(settings.get("header_enabled", True)))
        self.annotation_header_grouped.set(bool(settings.get("header_grouped", True)))
        self.annotation_in_image_enabled.set(bool(settings.get("in_image_enabled", False)))
        self.annotation_in_image_grouped.set(bool(settings.get("in_image_grouped", True)))
        visibility = settings.get("header_field_visibility", {})
        for key, variable in self.annotation_label_enabled.items():
            variable.set(bool(visibility.get(key, True)))
        self.annotation_strain_size.set(str(settings.get("strain_font_size", 18)))
        self.annotation_vertical_size.set(str(settings.get("vertical_font_size", 18)))
        self.annotation_rotation.set(str(settings.get("strain_rotation_degrees", 90)))
        self.annotation_source.set(str(settings.get("source_kind", self.annotation_source.get())))

    def _figure_description_toggled(self) -> None:
        if self.annotation_label_enabled["figure_description"].get():
            self.annotation_label_enabled["plate"].set(False)
            self.annotation_label_enabled["condition"].set(False)

    def _apply_annotation_settings(self, settings: dict[str, Any]) -> None:
        self.annotation_preset_settings = settings
        self._sync_annotation_controls()
        self.status.set("Annotation style preset applied; preview to verify placement.")

    def open_annotation_settings(self) -> None:
        AnnotationSettingsDialog(self, self._annotation_preset(), self._apply_annotation_settings)

    def preview_annotation(self) -> None:
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.propose_annotation(
                uid,
                self._annotation_request(),
                self._annotation_preset(),
                source_kind=self.annotation_source.get(),
            )
        )
        if result:
            self.annotation_proposal, preview = result
            self.viewer.show(preview)
            warnings = self.annotation_proposal.get("warnings", [])
            self.status.set(
                "Annotation preview only; "
                f"{len(warnings)} placement warning(s). Adjust preset or accept."
            )

    def accept_annotation(self) -> None:
        if self.annotation_proposal is None:
            messagebox.showerror("Annotation", "Preview an annotation first.")
            return
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.accept_annotation(uid, self.annotation_proposal)
        )
        if result:
            _accepted, output, sidecar = result
            self.annotation_proposal = None
            self.status.set(
                f"Accepted annotated derivative: {output}\nRecord: {sidecar}"
            )
            self._advance_after_stage(uid, "annotation")

    def skip_annotation(self) -> None:
        selected = self._run(self._selected)
        if not selected:
            return
        workflow, uid = selected
        result = self._run(lambda: workflow.skip_derivative(uid, "annotation"))
        if result:
            self.annotation_proposal = None
            self.status.set("Annotation skipped for this image.")
            self._advance_after_stage(uid, "annotation")

    def refresh_batch_images(self) -> None:
        if not hasattr(self, "batch_tree"):
            return
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
        if self.workflow is None:
            return
        for uid, record in self.workflow.state["images"].items():
            def status(key: str, current: dict[str, Any] = record) -> str:
                value = current.get(key)
                return str(value.get("status", "—")) if isinstance(value, dict) else "—"
            grid = record.get("grid")
            self.batch_tree.insert("", "end", iid=uid, values=(uid, status("orientation"), status("crop"), status("grid") if not isinstance(grid, dict) else grid.get("status", "—"), status("visibility"), status("annotation")))

    def select_all_batch_images(self) -> None:
        self.batch_tree.selection_set(self.batch_tree.get_children())

    def _batch_selected_uids(self) -> list[str]:
        selected = list(self.batch_tree.selection())
        if not selected:
            raise ValueError("Select at least one image in the Batch tab.")
        return selected

    def start_manual_batch(self, stage: str) -> None:
        if stage not in {"orientation", "crop"}:
            raise ValueError("Manual batch stage must be orientation or crop.")
        selected = self._run(self._batch_selected_uids)
        if not selected:
            return
        self.batch_queue, self.batch_queue_stage, self.batch_queue_index = selected, stage, 0
        self._load_manual_batch_current()

    def _load_manual_batch_current(self) -> None:
        uid = self.batch_queue[self.batch_queue_index]
        self.image_uid.set(uid)
        self.load_selected_source()
        if self.batch_queue_stage == "orientation":
            self.start_orientation()
        else:
            self.start_crop_placement()
        self.status.set(f"{self.batch_queue_stage.title()} batch {self.batch_queue_index + 1}/{len(self.batch_queue)}: {uid}.")

    def _advance_manual_batch(self, completed_uid: str) -> None:
        if (
            not self.batch_queue_stage
            or self.batch_queue_index >= len(self.batch_queue)
            or self.batch_queue[self.batch_queue_index] != completed_uid
        ):
            return
        self.batch_queue_index += 1
        if self.batch_queue_index >= len(self.batch_queue):
            stage = self.batch_queue_stage
            self.batch_queue, self.batch_queue_stage, self.batch_queue_index = [], None, 0
            self.refresh_batch_images()
            self.status.set(f"{stage.title()} batch complete.")
            return
        self._load_manual_batch_current()

    def _advance_after_stage(self, completed_uid: str, stage: str) -> None:
        if (
            self.batch_queue_stage
            and self.batch_queue_index < len(self.batch_queue)
            and self.batch_queue[self.batch_queue_index] == completed_uid
        ):
            self._advance_manual_batch(completed_uid)
            return
        self.refresh_batch_images()
        if not self.auto_advance_images.get():
            self.load_selected_source()
            return
        if self.workflow is None:
            return
        following = next_pending_image_uid(
            self.workflow.state["images"], completed_uid, stage
        )
        if following is None:
            self.load_selected_source()
            self.status.set(f"{stage.replace('_', ' ').title()} sequence complete.")
            return
        self.image_uid.set(following)
        self.load_selected_source()
        starters: dict[str, Callable[[], Any]] = {
            "orientation": self.start_orientation,
            "crop": self.start_crop_placement,
            "culture": self.preview_culture_crop_export,
            "visibility": self.preview_visibility,
            "annotation": self.preview_annotation,
        }
        starter = starters.get(stage)
        if starter is None:
            self.status.set(
                f"Advanced to {following}; continue {stage.replace('_', ' ')}."
            )
        else:
            starter()

    def plan_selected_batch(self, stage: str) -> None:
        workflow, _uid = self._selected()
        uids = self._run(self._batch_selected_uids)
        if not uids:
            return
        if stage == "culture":
            signature = self._run(self._crop_export_signature_value)
            if signature is None:
                return
            _uid, tier, source_kind, states, columns, width, height = signature
            options = {"tier": tier, "source_kind": source_kind, "states": states, "columns": columns, "crop_width": width, "crop_height": height}
        elif stage == "visibility":
            options = {"preset": self.visibility_preset.get()}
        elif stage == "annotation":
            overrides = {key: value.get().strip() for key, value in self.annotation_labels.items() if value.get().strip()}
            preset = self._run(self._annotation_preset)
            if preset is None:
                return
            options = {"label_overrides": overrides, "preset": preset, "source_kind": self.annotation_source.get()}
        else:
            raise ValueError("Unknown batch stage.")
        plan = self._run(lambda: plan_automatic_batch(workflow, stage, uids, options=options))
        if plan:
            self.batch_plan = plan
            self.status.set(f"Batch dry-run valid: {len(plan['image_uids'])} images, {plan['output_count']} planned output(s); nothing written.")

    def accept_batch_plan(self) -> None:
        if self.batch_plan is None:
            messagebox.showerror("Batch", "Create a current batch plan first.")
            return
        if not messagebox.askyesno("Accept batch", f"Accept {self.batch_plan['stage']} for {len(self.batch_plan['image_uids'])} preflighted images?"):
            return
        workflow, _uid = self._selected()
        result = self._run(lambda: execute_automatic_batch(workflow, self.batch_plan))
        if result:
            self.batch_plan = None
            self.refresh_batch_images()
            self.status.set(f"Accepted batch {result['stage']} for {len(result['image_uids'])} images.")

    def batch_attach_grids(self) -> None:
        workflow, _uid = self._selected()
        uids = self._run(self._batch_selected_uids)
        if not uids:
            return
        directory = filedialog.askdirectory(title="Folder containing per-image grid JSON assets")
        if not directory:
            return
        plan = self._run(lambda: plan_grid_directory(directory, uids))
        if not plan or not messagebox.askyesno("Attach grids", f"Attach {len(plan['items'])} validated, uniquely matched grid assets?"):
            return
        result = self._run(lambda: execute_grid_batch(workflow, plan))
        if result:
            self.refresh_batch_images()
            self.status.set(f"Attached grids for {len(result['image_uids'])} images.")

    def refresh_mixed_matrix_candidates(self) -> None:
        workflow, _uid = self._selected()
        candidates = self._run(workflow.mixed_tier_crop_candidates)
        if candidates is None:
            return
        self.matrix_candidates = candidates
        self.matrix_plan = None
        self.matrix_signature = None
        for item in self.matrix_tree.get_children():
            self.matrix_tree.delete(item)
        for candidate_id, candidate in candidates.items():
            context = candidate["context"]
            shown_context = " / ".join(
                context[key]
                for key in ("exp", "set", "condition", "date")
                if context[key]
            )
            self.matrix_tree.insert(
                "",
                "end",
                iid=candidate_id,
                values=(
                    candidate["state"],
                    candidate["source_tier"],
                    candidate["strain"],
                    candidate["image_uid"],
                    shown_context,
                ),
            )
        self.status.set(
            f"Loaded {len(candidates)} current verified crop candidate(s). "
            "Select one crop for every intended strain × image cell."
        )

    def _mixed_matrix_signature_value(self) -> tuple[Any, ...]:
        selected = tuple(self.matrix_tree.selection())
        if not selected:
            raise ValueError("Select crops for the mixed matrix first.")
        width_text = self.matrix_tile_width.get().strip()
        height_text = self.matrix_tile_height.get().strip()
        if bool(width_text) != bool(height_text):
            raise ValueError("Set both matrix tile dimensions or leave both blank.")
        tile_size = (
            (int(width_text), int(height_text)) if width_text and height_text else None
        )
        if tile_size is not None and any(value < 1 for value in tile_size):
            raise ValueError("Matrix tile dimensions must be positive integers.")
        save_last("mixed_matrix", {
            "layout_mode": self.matrix_layout_mode.get(),
            "tile_width": width_text,
            "tile_height": height_text,
        })
        return selected, tile_size, self.matrix_layout_mode.get()

    def preview_mixed_tier_matrix(self) -> None:
        workflow, _uid = self._selected()
        signature = self._run(self._mixed_matrix_signature_value)
        if signature is None:
            return
        selected, tile_size, layout_mode = signature
        chosen = [self.matrix_candidates[candidate_id] for candidate_id in selected]
        if layout_mode == "Selected crops (one column)":
            rows = [
                (
                    f"{candidate['strain']} "
                    f"[{candidate['state']} | {candidate['image_uid']} | "
                    f"{candidate['candidate_id'][-6:]}]"
                )
                for candidate in chosen
            ]
            columns = ["Selected"]
            selections = [
                {
                    "candidate_id": candidate["candidate_id"],
                    "row": row,
                    "column": "Selected",
                }
                for candidate, row in zip(chosen, rows, strict=True)
            ]
        else:
            rows = list(dict.fromkeys(candidate["default_row"] for candidate in chosen))
            columns = list(
                dict.fromkeys(candidate["default_column"] for candidate in chosen)
            )
            selections = [
                {
                    "candidate_id": candidate["candidate_id"],
                    "row": candidate["default_row"],
                    "column": candidate["default_column"],
                }
                for candidate in chosen
            ]
        result = self._run(
            lambda: workflow.propose_mixed_tier_matrix(
                selections,
                rows=rows,
                columns=columns,
                tile_size=tile_size,
            )
        )
        if result:
            self.matrix_plan, preview = result
            self.matrix_signature = signature
            self.viewer.show(preview)
            self.status.set(
                f"Mixed matrix preview: {len(selections)} cells, "
                f"{len(rows)} row(s) × {len(columns)} column(s); no files written."
            )

    def accept_mixed_tier_matrix(self) -> None:
        workflow, _uid = self._selected()
        signature = self._run(self._mixed_matrix_signature_value)
        if signature is None:
            return
        if self.matrix_plan is None or self.matrix_signature != signature:
            messagebox.showerror(
                "Mixed matrix",
                "Preview the current crop selection, layout and tile size first.",
            )
            return
        if not messagebox.askyesno(
            "Export mixed matrix",
            f"Publish the previewed {len(self.matrix_plan['items'])}-cell matrix "
            "to a new numbered run?",
        ):
            return
        result = self._run(lambda: workflow.accept_mixed_tier_matrix(self.matrix_plan))
        if result:
            self.matrix_plan = None
            self.matrix_signature = None
            self.status.set(f"Accepted mixed matrix: {result['output_path']}")

    def _refresh_asset_labels(self) -> None:
        if self.workflow is None or not self.image_uid.get():
            return
        record = self.workflow.image_record(self.image_uid.get())
        grid = record.get("grid")
        if isinstance(grid, dict):
            self.grid_label.configure(
                text=f"{grid.get('status')}: {grid.get('asset_id')}\n{grid.get('path')}"
            )
        else:
            self.grid_label.configure(text="No current grid asset")
        try:
            request = self.workflow.default_annotation_request(self.image_uid.get())
        except ValueError:
            for variable in self.annotation_labels.values():
                variable.set("")
        else:
            for key, variable in self.annotation_labels.items():
                variable.set(str(request["labels"].get(key, "")))
        calibrations = self.workflow.state.get("crop_calibrations", {})
        if calibrations:
            self._refresh_crop_calibration_presets()
        else:
            self.crop_calibration_box.configure(values=())
            self.crop_calibration_id.set("")
            self.calibration_label.configure(text="No accepted calibration")


def main() -> int:
    app = WorkflowApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
