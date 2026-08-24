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


def calibrate_crop_size(
    left_pt: tuple[float, float],
    right_pt: tuple[float, float],
    top_pt: tuple[float, float],
    bottom_pt: tuple[float, float],
    increment: int = 50,
    calibration_id: str | None = None,
    *,
    accepted: bool = False,
) -> dict[str, Any]:
    """Derive a proposed or accepted reusable square crop-size calibration."""
    if not isinstance(increment, int) or increment <= 0:
        raise ValueError(f"increment must be a positive integer, got {increment}")
    measured_width = abs(float(right_pt[0]) - float(left_pt[0]))
    measured_height = abs(float(bottom_pt[1]) - float(top_pt[1]))
    if not all(
        math.isfinite(value) and value > 0
        for value in (measured_width, measured_height)
    ):
        raise ValueError(
            "Boundary points must define positive finite width and height."
        )
    side = int(math.floor(min(measured_width, measured_height) / increment) * increment)
    if side <= 0:
        raise ValueError("Calculated crop side must be positive.")
    return {
        "contract_version": 1,
        "asset_type": "CropSizeCalibration",
        "status": "ACCEPTED" if accepted else "PROPOSED",
        "calibration_id": calibration_id or "calib_default",
        "side_pixels": side,
        "is_square": True,
        "rounding_increment": increment,
        "measured_extents": {
            "measured_width": round(measured_width, 2),
            "measured_height": round(measured_height, 2),
            "left_x": float(left_pt[0]),
            "right_x": float(right_pt[0]),
            "top_y": float(top_pt[1]),
            "bottom_y": float(bottom_pt[1]),
        },
        "method": "four_boundary_points_floor_increment",
    }


def _dimensions(image_geometry: dict[str, Any]) -> tuple[int, int] | None:
    width, height = image_geometry.get("width"), image_geometry.get("height")
    if width is None and height is None:
        return None
    if (
        not isinstance(width, int)
        or width < 1
        or not isinstance(height, int)
        or height < 1
    ):
        raise ValueError("Crop placement dimensions must be positive integers.")
    return width, height


def place_plate_crop(
    calibration: dict[str, Any],
    left_edge_pt: tuple[float, float],
    top_edge_pt: tuple[float, float],
    image_geometry: dict[str, Any] | None = None,
    inset_offset: tuple[int, int] = (0, 0),
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Place a reusable crop size using independent per-image left/top anchors."""
    options = options or {}
    image_geometry = image_geometry or {}
    dimensions = _dimensions(image_geometry)
    image_uid = (
        options.get("image_uid") or image_geometry.get("image_uid") or "unknown_image"
    )
    if options.get("skip"):
        return {
            "contract_version": 1,
            "asset_type": "CropResult",
            "status": "SKIPPED",
            "image_uid": str(image_uid),
            "calibration_id": calibration.get("calibration_id", "none"),
            "crop_box": None,
            "source_dimensions": list(dimensions) if dimensions else None,
            "output_dimensions": list(dimensions) if dimensions else None,
            "transform": None,
            "output_path": None,
        }
    if calibration.get("status", "ACCEPTED") != "ACCEPTED":
        raise ValueError("Crop-size calibration must be accepted before placement.")
    side = calibration.get("side_pixels")
    if not isinstance(side, int) or side <= 0:
        raise ValueError(f"Invalid calibration side_pixels: {side}")
    x_anchor, y_anchor = float(left_edge_pt[0]), float(top_edge_pt[1])
    if not math.isfinite(x_anchor) or not math.isfinite(y_anchor):
        raise ValueError("Crop anchors must be finite.")
    left = round(x_anchor + inset_offset[0])
    top = round(y_anchor + inset_offset[1])
    right, bottom = left + side, top + side
    if dimensions and (
        left < 0 or top < 0 or right > dimensions[0] or bottom > dimensions[1]
    ):
        raise ValueError(
            f"Proposed crop ({left}, {top}, {right}, {bottom}) is outside source dimensions {dimensions}."
        )
    status = "ACCEPTED" if options.get("accepted") else "PROPOSED"
    return {
        "contract_version": 1,
        "asset_type": "CropResult",
        "status": status,
        "image_uid": str(image_uid),
        "calibration_id": calibration.get("calibration_id", "calib_default"),
        "crop_box": {
            "x": left,
            "y": top,
            "width": side,
            "height": side,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        },
        "left_anchor_x": x_anchor,
        "top_anchor_y": y_anchor,
        "source_dimensions": list(dimensions) if dimensions else None,
        "output_dimensions": [side, side],
        "transform": {
            "model": "source_to_crop_translation",
            "matrix": [[1.0, 0.0, -left], [0.0, 1.0, -top], [0.0, 0.0, 1.0]],
        },
        "output_path": options.get("output_path"),
    }


def _prepare_output(path: str | Path) -> Path:
    output = Path(path)
    if output.parent != Path("."):
        output.parent.mkdir(parents=True, exist_ok=True)
    return output


def apply_plate_crop(
    source_image: str | Path | Any,
    crop_result: dict[str, Any],
    output_path: str | Path | None = None,
) -> Any:
    """Preview or non-destructively write an accepted whole-plate crop."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for apply_plate_crop")
    status = crop_result.get("status", "ACCEPTED")
    crop_box = crop_result.get("crop_box")
    if output_path and status not in {"ACCEPTED", "SKIPPED"}:
        raise ValueError("A proposed crop cannot be written before acceptance.")

    def transform(image):
        if status == "SKIPPED" or crop_box is None:
            return image.copy()
        expected = crop_result.get("source_dimensions")
        if expected and list(image.size) != expected:
            raise ValueError("Source dimensions do not match CropResult.")
        box = tuple(crop_box[key] for key in ("left", "top", "right", "bottom"))
        return image.crop(box)

    if isinstance(source_image, (str, Path)):
        source = Path(source_image)
        if not source.is_file():
            raise FileNotFoundError(f"Source image does not exist: {source}")
        if status == "SKIPPED" and output_path:
            output = _prepare_output(output_path)
            shutil.copy2(source, output)
            return str(output)
        with Image.open(source) as image:
            result = transform(image)
            if output_path:
                output = _prepare_output(output_path)
                result.save(output)
                return str(output)
            return result

    result = transform(source_image)
    if output_path:
        output = _prepare_output(output_path)
        result.save(output)
        return str(output)
    return result


def transform_point_to_crop(
    x: float, y: float, crop_result: dict[str, Any]
) -> tuple[float, float]:
    crop_box = crop_result.get("crop_box")
    if not crop_box:
        return x, y
    return x - crop_box["x"], y - crop_box["y"]


def transform_point_from_crop_to_source(
    crop_x: float, crop_y: float, crop_result: dict[str, Any]
) -> tuple[float, float]:
    crop_box = crop_result.get("crop_box")
    if not crop_box:
        return crop_x, crop_y
    return crop_x + crop_box["x"], crop_y + crop_box["y"]
