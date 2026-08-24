from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def compute_line_angle(
    x1: float, y1: float, x2: float, y2: float
) -> tuple[float, float]:
    """Return observed screen-space slope and the Pillow correction angle."""
    if abs(x2 - x1) < 1e-9 and abs(y2 - y1) < 1e-9:
        raise ValueError("Line endpoints cannot be identical.")
    if x2 < x1:
        x1, y1, x2, y2 = x2, y2, x1, y1
    observed = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return observed, observed


def transform_point_around_center(
    x: float,
    y: float,
    cx: float,
    cy: float,
    angle_degrees: float,
) -> tuple[float, float]:
    """Map a source point through Pillow's screen-coordinate rotation."""
    radians = math.radians(angle_degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return (
        cx + (x - cx) * cosine + (y - cy) * sine,
        cy - (x - cx) * sine + (y - cy) * cosine,
    )


def _rotation_transform(width: int, height: int, angle: float) -> dict[str, Any]:
    cx, cy = width / 2.0, height / 2.0
    radians = math.radians(angle)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    return {
        "model": "rotation_about_image_centre",
        "coordinate_space": "source_image_pixels",
        "centre": {"x": cx, "y": cy},
        "expand": False,
        "matrix": [
            [cosine, sine, cx - cx * cosine - cy * sine],
            [-sine, cosine, cy + cx * sine - cy * cosine],
            [0.0, 0.0, 1.0],
        ],
        "source_dimensions": [width, height],
        "output_dimensions": [width, height],
        "clipping_policy": "preserve_dimensions",
    }


def _geometry(image_geometry: dict[str, Any]) -> tuple[int, int]:
    width, height = image_geometry.get("width"), image_geometry.get("height")
    if (
        not isinstance(width, int)
        or width < 1
        or not isinstance(height, int)
        or height < 1
    ):
        raise ValueError(
            "Orientation capture requires positive source width and height."
        )
    return width, height


def capture_plate_orientation(
    line: dict[str, float]
    | tuple[float, float, float, float]
    | list[float]
    | None = None,
    image_geometry: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a proposed, accepted, or skipped OrientationResult v1."""
    options = options or {}
    image_geometry = image_geometry or {}
    skip = bool(options.get("skip"))
    width = image_geometry.get("width")
    height = image_geometry.get("height")
    image_uid = options.get("image_uid") or image_geometry.get("image_uid")
    method = options.get("method", "manual_horizontal_edge_line")

    if skip or line is None:
        transform = None
        if (
            isinstance(width, int)
            and width > 0
            and isinstance(height, int)
            and height > 0
        ):
            transform = _rotation_transform(width, height, 0.0)
        return {
            "contract_version": 1,
            "status": "SKIPPED",
            "image_uid": image_uid,
            "angle_degrees": 0.0,
            "confidence": None,
            "method": method,
            "needs_manual_review": False,
            "source_path": options.get("source_path"),
            "output_path": options.get("output_path"),
            "transform": transform,
            "diagnostics": {
                "line": None,
                "observed_angle_degrees": 0.0,
                "convention": "pil_counter_clockwise_positive",
            },
        }

    width, height = _geometry(image_geometry)
    if isinstance(line, dict):
        x1, y1, x2, y2 = (line[key] for key in ("x1", "y1", "x2", "y2"))
    elif isinstance(line, (list, tuple)) and len(line) == 4:
        x1, y1, x2, y2 = line
    else:
        raise ValueError(f"Invalid line format: {line}")
    values = [float(x1), float(y1), float(x2), float(y2)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Orientation line coordinates must be finite.")
    observed, correction = compute_line_angle(*values)
    status = "ACCEPTED" if options.get("accepted") else "PROPOSED"
    return {
        "contract_version": 1,
        "status": status,
        "image_uid": image_uid,
        "angle_degrees": round(correction, 4),
        "confidence": 1.0 if status == "ACCEPTED" else None,
        "method": method,
        "needs_manual_review": status != "ACCEPTED",
        "source_path": options.get("source_path"),
        "output_path": options.get("output_path"),
        "transform": _rotation_transform(width, height, correction),
        "diagnostics": {
            "line": {
                "x1": values[0],
                "y1": values[1],
                "x2": values[2],
                "y2": values[3],
            },
            "observed_angle_degrees": round(observed, 4),
            "correction_angle_degrees": round(correction, 4),
            "edge_used": options.get("edge_used", "top_or_bottom"),
            "convention": "pil_counter_clockwise_positive",
        },
    }


def _prepare_output(path: str | Path) -> Path:
    output = Path(path)
    if output.parent != Path("."):
        output.parent.mkdir(parents=True, exist_ok=True)
    return output


def apply_plate_orientation(
    source_image: str | Path | Any,
    orientation_result: dict[str, Any],
    output_path: str | Path | None = None,
    resample_filter: int | None = None,
) -> Any:
    """Preview or non-destructively write an accepted orientation derivative."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for apply_plate_orientation")
    status = orientation_result.get("status", "ACCEPTED")
    if output_path and status not in {"ACCEPTED", "SKIPPED"}:
        raise ValueError("A proposed orientation cannot be written before acceptance.")
    angle = float(orientation_result.get("angle_degrees", 0.0))
    filter_mode = resample_filter or Image.Resampling.BICUBIC

    if isinstance(source_image, (str, Path)):
        source = Path(source_image)
        if not source.is_file():
            raise FileNotFoundError(f"Source image does not exist: {source}")
        if status == "SKIPPED" or abs(angle) < 1e-5:
            if output_path:
                output = _prepare_output(output_path)
                shutil.copy2(source, output)
                return str(output)
            with Image.open(source) as image:
                return image.copy()
        with Image.open(source) as image:
            expected = orientation_result.get("transform", {}).get("source_dimensions")
            if expected and list(image.size) != expected:
                raise ValueError("Source dimensions do not match OrientationResult.")
            rotated = image.rotate(angle, resample=filter_mode, expand=False)
            if output_path:
                output = _prepare_output(output_path)
                rotated.save(output)
                return str(output)
            return rotated

    image = source_image
    if status == "SKIPPED" or abs(angle) < 1e-5:
        return image.copy()
    rotated = image.rotate(angle, resample=filter_mode, expand=False)
    if output_path:
        output = _prepare_output(output_path)
        rotated.save(output)
        return str(output)
    return rotated
