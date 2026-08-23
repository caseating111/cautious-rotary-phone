import math
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def calibrate_crop_size(
    left_pt: Tuple[float, float],
    right_pt: Tuple[float, float],
    top_pt: Tuple[float, float],
    bottom_pt: Tuple[float, float],
    increment: int = 50,
    calibration_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Derives reusable square CropSizeCalibration from 4 boundary points (left, right, top, bottom).
    Exact corners are NOT required.
    
    Rule:
    - measured_width = abs(right_pt[0] - left_pt[0])
    - measured_height = abs(bottom_pt[1] - top_pt[1])
    - raw_side = min(measured_width, measured_height)
    - side_pixels = floor(raw_side / increment) * increment
    """
    if increment <= 0:
        raise ValueError(f"increment must be a positive integer, got {increment}")

    measured_w = abs(right_pt[0] - left_pt[0])
    measured_h = abs(bottom_pt[1] - top_pt[1])

    if measured_w <= 0 or measured_h <= 0:
        raise ValueError(f"Invalid boundary points: measured_w={measured_w}, measured_h={measured_h}")

    raw_side = min(measured_w, measured_h)
    side_pixels = int(math.floor(raw_side / increment) * increment)

    if side_pixels <= 0:
        raise ValueError(f"Calculated side_pixels ({side_pixels}) must be > 0. Check boundary points and increment.")

    return {
        "contract_version": 1,
        "calibration_id": calibration_id or "calib_default",
        "side_pixels": side_pixels,
        "is_square": True,
        "rounding_increment": increment,
        "measured_extents": {
            "measured_width": round(measured_w, 2),
            "measured_height": round(measured_h, 2),
            "left_x": left_pt[0],
            "right_x": right_pt[0],
            "top_y": top_pt[1],
            "bottom_y": bottom_pt[1]
        },
        "method": "four_boundary_points_floor_increment"
    }


def place_plate_crop(
    calibration: Dict[str, Any],
    left_edge_pt: Tuple[float, float],
    top_edge_pt: Tuple[float, float],
    image_geometry: Optional[Dict[str, Any]] = None,
    inset_offset: Tuple[int, int] = (0, 0),
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Places a calibrated crop square onto an image using 2 independent anchor clicks:
    - left_edge_pt[0]: authoritative X anchor
    - top_edge_pt[1]: authoritative Y anchor
    
    Returns CropResult dict.
    """
    options = options or {}
    image_geometry = image_geometry or {}
    skip = options.get("skip", False)
    image_uid = options.get("image_uid") or image_geometry.get("image_uid") or "unknown_image"

    if skip:
        return {
            "contract_version": 1,
            "image_uid": str(image_uid),
            "calibration_id": calibration.get("calibration_id", "none"),
            "status": "SKIPPED",
            "crop_box": None,
            "left_anchor_x": None,
            "top_anchor_y": None,
            "source_dimensions": [image_geometry.get("width"), image_geometry.get("height")] if image_geometry else None,
            "output_dimensions": [image_geometry.get("width"), image_geometry.get("height")] if image_geometry else None,
            "needs_manual_review": False,
            "output_path": None
        }

    side = calibration.get("side_pixels")
    if not isinstance(side, int) or side <= 0:
        raise ValueError(f"Invalid calibration side_pixels: {side}")

    x_anchor = left_edge_pt[0]
    y_anchor = top_edge_pt[1]

    crop_x = int(round(x_anchor + inset_offset[0]))
    crop_y = int(round(y_anchor + inset_offset[1]))

    crop_box = {
        "x": crop_x,
        "y": crop_y,
        "width": side,
        "height": side,
        "left": crop_x,
        "top": crop_y,
        "right": crop_x + side,
        "bottom": crop_y + side
    }

    return {
        "contract_version": 1,
        "image_uid": str(image_uid),
        "calibration_id": calibration.get("calibration_id", "calib_default"),
        "status": "ACCEPTED",
        "crop_box": crop_box,
        "left_anchor_x": float(x_anchor),
        "top_anchor_y": float(y_anchor),
        "source_dimensions": [image_geometry.get("width"), image_geometry.get("height")] if image_geometry else None,
        "output_dimensions": [side, side],
        "needs_manual_review": False,
        "output_path": options.get("output_path")
    }


def apply_plate_crop(
    source_image: Union[str, Any],
    crop_result: Dict[str, Any],
    output_path: Optional[str] = None
) -> Any:
    """
    Applies CropResult to source image non-destructively.
    If status is SKIPPED, simply copies or returns source.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for apply_plate_crop")

    status = crop_result.get("status", "ACCEPTED")
    crop_box = crop_result.get("crop_box")

    if isinstance(source_image, str):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' does not exist")

        if status == "SKIPPED" or crop_box is None:
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy2(source_image, output_path)
                return output_path
            return Image.open(source_image)

        with Image.open(source_image) as img:
            box = (crop_box["left"], crop_box["top"], crop_box["right"], crop_box["bottom"])
            cropped = img.crop(box)
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                cropped.save(output_path)
                return output_path
            return cropped
    else:
        # source_image is PIL Image
        img = source_image
        if status == "SKIPPED" or crop_box is None:
            return img.copy()
        box = (crop_box["left"], crop_box["top"], crop_box["right"], crop_box["bottom"])
        cropped = img.crop(box)
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cropped.save(output_path)
            return output_path
        return cropped


def transform_point_to_crop(
    x: float,
    y: float,
    crop_result: Dict[str, Any]
) -> Tuple[float, float]:
    """
    Transforms coordinate (x, y) from source image space to cropped image space.
    """
    crop_box = crop_result.get("crop_box")
    if not crop_box:
        return x, y
    return x - crop_box["x"], y - crop_box["y"]


def transform_point_from_crop_to_source(
    crop_x: float,
    crop_y: float,
    crop_result: Dict[str, Any]
) -> Tuple[float, float]:
    """
    Transforms coordinate (crop_x, crop_y) from cropped space back to source image space.
    """
    crop_box = crop_result.get("crop_box")
    if not crop_box:
        return crop_x, crop_y
    return crop_x + crop_box["x"], crop_y + crop_box["y"]

