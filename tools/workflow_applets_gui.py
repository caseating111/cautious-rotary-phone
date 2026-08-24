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

from tools.applet_workflows import ProjectWorkflow
from tools.applets.plate_crop import calibrate_crop_size


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
        px = (x - self.offset[0]) / self.scale
        py = (y - self.offset[1]) / self.scale
        if 0 <= px < self.image.width and 0 <= py < self.image.height:
            return px, py
        return None

    def draw_points(self, points: list[tuple[float, float]]) -> None:
        self.clear_overlays()
        for index, (x, y) in enumerate(points, start=1):
            cx = self.offset[0] + x * self.scale
            cy = self.offset[1] + y * self.scale
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
            self.offset[0] + start[0] * self.scale,
            self.offset[1] + start[1] * self.scale,
            self.offset[0] + end[0] * self.scale,
            self.offset[1] + end[1] * self.scale,
        ]
        self.canvas.create_line(*coords, fill="#00ffff", width=3, tags="overlay")

    def draw_box(self, box: dict[str, Any]) -> None:
        self.clear_overlays()
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
            self.canvas.create_text(
                410,
                280,
                text="Open a project and select an image",
                fill="#dddddd",
            )
            return
        width = max(self.canvas.winfo_width(), 100)
        height = max(self.canvas.winfo_height(), 100)
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
        self.calibration_points: list[tuple[float, float]] = []
        self.calibration_proposal: dict[str, Any] | None = None
        self.crop_points: list[tuple[float, float]] = []
        self.crop_proposal: dict[str, Any] | None = None
        self.crop_previewed = False
        self.raw_root_var = tk.StringVar()
        self.enable_rename = tk.BooleanVar(value=True)
        self.setup_preview: dict[str, Any] | None = None
        self.setup_signature: tuple[str, bool] | None = None
        self.visibility_preset = tk.StringVar(value="background_aware_linear")
        self.visibility_proposal: dict[str, Any] | None = None
        self.annotation_proposal: dict[str, Any] | None = None
        self.annotation_labels = {
            key: tk.StringVar() for key in ("date", "plate", "condition", "session")
        }
        self.annotation_strain_size = tk.StringVar(value="18")
        self.annotation_vertical_size = tk.StringVar(value="18")
        self.annotation_rotation = tk.StringVar(value="90")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Create from V10…", command=self.create_project).pack(
            side="left"
        )
        ttk.Button(top, text="Open project…", command=self.open_project).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(top, text="Image UID").pack(side="left", padx=(18, 5))
        self.image_picker = ttk.Combobox(
            top, textvariable=self.image_uid, state="readonly", width=34
        )
        self.image_picker.pack(side="left")
        self.image_picker.bind("<<ComboboxSelected>>", self.load_selected_source)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8)
        controls = ttk.Frame(body, width=390)
        body.add(controls, weight=0)
        self.viewer = ImageCanvas(body)
        body.add(self.viewer, weight=1)

        notebook = ttk.Notebook(controls)
        notebook.pack(fill="both", expand=True)
        setup = ttk.Frame(notebook)
        orientation = ttk.Frame(notebook)
        crop = ttk.Frame(notebook)
        grid = ttk.Frame(notebook)
        visibility = ttk.Frame(notebook)
        annotation = ttk.Frame(notebook)
        notebook.add(setup, text="Setup")
        notebook.add(orientation, text="Orientation")
        notebook.add(crop, text="Plate crop")
        notebook.add(grid, text="Grid asset")
        notebook.add(visibility, text="Visibility")
        notebook.add(annotation, text="Annotation")

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
        setup_actions = ttk.Frame(setup)
        setup_actions.pack(fill="x", padx=8, pady=3)
        ttk.Button(
            setup_actions, text="Preview", command=self.preview_project_setup
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(setup_actions, text="Apply", command=self.apply_project_setup).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        self.setup_tree = ttk.Treeview(
            setup,
            columns=("raw", "uid", "working", "status"),
            show="headings",
            height=18,
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
            text="Drag one line along a top or bottom plate edge, preview, then accept.",
            wraplength=245,
        ).pack(anchor="w", padx=8, pady=8)
        ttk.Button(
            orientation, text="Start / retry line", command=self.start_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Preview correction", command=self.preview_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Accept orientation", command=self.accept_orientation
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            orientation, text="Skip orientation", command=self.skip_orientation
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
            crop, text="Recalibrate size (4 clicks)", command=self.start_calibration
        ).pack(fill="x", padx=8, pady=3)
        self.calibration_label = ttk.Label(crop, text="No accepted calibration")
        self.calibration_label.pack(anchor="w", padx=8, pady=3)
        ttk.Button(
            crop, text="Accept size calibration", command=self.accept_calibration
        ).pack(fill="x", padx=8, pady=3)
        ttk.Separator(crop).pack(fill="x", padx=8, pady=8)
        ttk.Button(
            crop, text="Place crop (left, top)", command=self.start_crop_placement
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(crop, text="Preview crop", command=self.preview_crop).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(crop, text="Accept crop", command=self.accept_crop).pack(
            fill="x", padx=8, pady=3
        )
        ttk.Button(
            crop, text="Retry placement", command=self.start_crop_placement
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(crop, text="Skip crop", command=self.skip_crop).pack(
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
        ttk.Button(grid, text="Attach grid asset…", command=self.attach_grid).pack(
            fill="x", padx=8, pady=3
        )
        self.grid_label = ttk.Label(grid, text="No current grid asset", wraplength=245)
        self.grid_label.pack(anchor="w", padx=8, pady=6)
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
            visibility, text="Preview adjustment", command=self.preview_visibility
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility,
            text="Accept processed derivative",
            command=self.accept_visibility,
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            visibility, text="Flag for manual review", command=self.flag_visibility
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
        for key, label in (
            ("date", "Date"),
            ("plate", "Plate"),
            ("condition", "Condition"),
            ("session", "Session"),
        ):
            row = ttk.Frame(annotation)
            row.pack(fill="x", padx=8, pady=2)
            ttk.Label(row, text=label, width=11).pack(side="left")
            ttk.Entry(row, textvariable=self.annotation_labels[key]).pack(
                side="left", fill="x", expand=True
            )
        for variable, label in (
            (self.annotation_strain_size, "Strain font"),
            (self.annotation_vertical_size, "Vertical font"),
            (self.annotation_rotation, "Strain rotation"),
        ):
            row = ttk.Frame(annotation)
            row.pack(fill="x", padx=8, pady=2)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=variable, width=8).pack(side="left")
        ttk.Button(
            annotation, text="Preview annotation", command=self.preview_annotation
        ).pack(fill="x", padx=8, pady=(8, 3))
        ttk.Button(
            annotation,
            text="Accept annotated derivative",
            command=self.accept_annotation,
        ).pack(fill="x", padx=8, pady=3)
        ttk.Button(
            annotation, text="Return to source", command=self.load_selected_source
        ).pack(fill="x", padx=8, pady=3)

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

    def open_project(self) -> None:
        root = filedialog.askdirectory(title="Select the project root folder")
        if not root:
            return
        workflow = self._run(lambda: ProjectWorkflow.open(root))
        if workflow:
            self._activate(workflow)

    def _activate(self, workflow: ProjectWorkflow) -> None:
        self.workflow = workflow
        self.raw_root_var.set(str(workflow.project_root / "Raw"))
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

    def _setup_signature_value(self) -> tuple[str, bool]:
        raw = self.raw_root_var.get().strip()
        if not raw:
            workflow, _uid = self._selected()
            raw = str(workflow.project_root / "Raw")
            self.raw_root_var.set(raw)
        return str(Path(raw).resolve()), self.enable_rename.get()

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
                raw_root=signature[0], enable_rename=signature[1]
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
        if not messagebox.askyesno(
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
                raw_root=signature[0], enable_rename=signature[1]
            )
        )
        if result:
            self.setup_preview = None
            self.setup_signature = None
            self._show_setup_result(result)
            self.status.set(
                f"Setup applied: {result['summary']['copied_count']} copied; "
                "project state and conversion audit map saved."
            )
            self.load_selected_source()

    def start_orientation(self) -> None:
        def action() -> None:
            workflow, uid = self._selected()
            source = workflow.source_for(uid, include_crop=False)
            with Image.open(source) as image:
                self.viewer.show(image)
            self.orientation_proposal = None
            self.viewer.set_handlers(drag=self._orientation_dragged)
            self.status.set(
                "Drag a line from left to right along a horizontal plate edge."
            )

        self._run(action)

    def _orientation_dragged(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> None:
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.propose_orientation(uid, (*start, *end)))
        if result:
            self.orientation_proposal, _preview = result
            line = self.orientation_proposal["diagnostics"]["line"]
            self.viewer.draw_line((line["x1"], line["y1"]), (line["x2"], line["y2"]))
            self.status.set(
                f"Proposed correction: {self.orientation_proposal['angle_degrees']:.4f}°. Preview before accepting."
            )

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
            self.load_selected_source()

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
                self.load_selected_source()

    def start_calibration(self) -> None:
        def action() -> None:
            workflow, uid = self._selected()
            source = workflow.source_for(uid, include_crop=False)
            with Image.open(source) as image:
                self.viewer.show(image)
            self.calibration_points = []
            self.calibration_proposal = None
            self.viewer.set_handlers(click=self._calibration_clicked)
            self.status.set(
                "Click useful boundaries in order: left, right, top, bottom."
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
        self.calibration_proposal = self._run(
            lambda: calibrate_crop_size(*self.calibration_points)
        )
        if self.calibration_proposal:
            side = self.calibration_proposal["side_pixels"]
            self.calibration_label.configure(text=f"Proposed size: {side} × {side} px")
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
        result = self._run(
            lambda: workflow.accept_crop_calibration(
                *self.calibration_points, calibration_id=calibration_id
            )
        )
        if result:
            self.calibration_label.configure(
                text=f"Accepted {calibration_id}: {result['side_pixels']} × {result['side_pixels']} px"
            )
            self.status.set(
                "Crop size accepted and reusable; placement remains per image."
            )

    def _current_calibration_id(self) -> str:
        workflow, _uid = self._selected()
        if not workflow.state["crop_calibrations"]:
            raise ValueError("Accept a crop-size calibration first.")
        return next(reversed(workflow.state["crop_calibrations"]))

    def start_crop_placement(self) -> None:
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
            self.load_selected_source()

    def skip_crop(self) -> None:
        workflow, uid = self._selected()
        result = self._run(lambda: workflow.skip_crop(uid))
        if result:
            self.crop_proposal = None
            self.status.set(
                "Plate crop skipped; the existing four-point route remains available."
            )
            self.load_selected_source()

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

    def preview_visibility(self) -> None:
        workflow, uid = self._selected()
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
            self.load_selected_source()

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
            self.load_selected_source()

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
        return {
            "name": "user_preview",
            "strain_font_size": strain_size,
            "vertical_font_size": vertical_size,
            "strain_rotation_degrees": rotation,
        }

    def preview_annotation(self) -> None:
        workflow, uid = self._selected()
        result = self._run(
            lambda: workflow.propose_annotation(
                uid, self._annotation_request(), self._annotation_preset()
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
            calibration_id = next(reversed(calibrations))
            calibration = calibrations[calibration_id]
            self.calibration_label.configure(
                text=f"Accepted {calibration_id}: {calibration['side_pixels']} × {calibration['side_pixels']} px"
            )


def main() -> int:
    app = WorkflowApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
