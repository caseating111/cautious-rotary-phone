import math
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def compute_line_angle(
    x1: float,
    y1: float,
    x2: float,
    y2: float
) -> Tuple[float, float]:
    """
    Calculates observed angle and required correction angle to make a line horizontal.
    
    Coordinate convention:
    - Screen coordinates (X increases rightwards, Y increases downwards).
    - If x2 < x1, endpoints are normalized so dx > 0 (left to right).
    - Observed angle theta = atan2(dy, dx) in degrees.
      - If dy > 0: line tilts downward to the right (clockwise tilt).
      - If dy < 0: line tilts upward to the right (counter-clockwise tilt).
    - Correction angle = -theta (in clockwise tilt) -> applying +theta counter-clockwise rotation straightens the line.
      For PIL/standard image rotation (which rotates counter-clockwise for positive degrees):
      rotation_angle_degrees = observed_angle_deg (or -observed_angle_deg depending on PIL convention).
      Specifically in PIL, rotating by +observed_angle_deg counter-clockwise rotates a point (x, y) around center:
      new_y = (x - cx)*sin(theta) + (y - cy)*cos(theta) + cy.
      When dy = y2 - y1 > 0 (clockwise tilt), PIL rotate(observed_angle_deg) straightens it.
    
    Returns:
    - (observed_angle_degrees, correction_angle_degrees)
    """
    if abs(x2 - x1) < 1e-9 and abs(y2 - y1) < 1e-9:
        raise ValueError("Line endpoints (x1, y1) and (x2, y2) cannot be identical")

    # Normalize left-to-right
    if x2 < x1:
        x1, y1, x2, y2 = x2, y2, x1, y1

    dx = x2 - x1
    dy = y2 - y1

    observed_rad = math.atan2(dy, dx)
    observed_deg = math.degrees(observed_rad)

    # Correction angle: PIL rotate by +observed_deg straightens positive-slope lines
    correction_deg = observed_deg

    return observed_deg, correction_deg


def transform_point_around_center(
    x: float,
    y: float,
    cx: float,
    cy: float,
    angle_degrees: float
) -> Tuple[float, float]:
    """
    Rotates point (x, y) around center (cx, cy) by angle_degrees (PIL convention: counter-clockwise).
    In screen coordinates where Y is down, rotating counter-clockwise by theta (radians):
    x' = cx + (x - cx)*cos(theta) + (y - cy)*sin(theta)
    y' = cy - (x - cx)*sin(theta) + (y - cy)*cos(theta)
    """
    rad = math.radians(angle_degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    nx = cx + (x - cx) * cos_a + (y - cy) * sin_a
    ny = cy - (x - cx) * sin_a + (y - cy) * cos_a
    return nx, ny


def capture_plate_orientation(
    line: Optional[Union[Dict[str, float], Tuple[float, float, float, float], List[float]]] = None,
    image_geometry: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculates OrientationResult v1 conforming to contracts/rotation_result.schema.json.
    
    Arguments:
    - line: {'x1': float, 'y1': float, 'x2': float, 'y2': float} or (x1, y1, x2, y2).
            If None or options.get('skip') is True, returns SKIPPED orientation result (angle 0.0).
    - image_geometry: Optional dict with {'width': int, 'height': int, 'image_uid': str}
    - options:
        - skip: bool (default False)
        - method: str (default "manual_horizontal_edge_line")
        - edge_used: str ("top" | "bottom" | "auto")
    """
    options = options or {}
    image_geometry = image_geometry or {}
    skip = options.get("skip", False)

    if skip or line is None:
        return {
            "contract_version": 1,
            "angle_degrees": 0.0,
            "confidence": 1.0,
            "method": options.get("method", "manual_horizontal_edge_line"),
            "needs_manual_review": False,
            "diagnostics": {
                "status": "SKIPPED",
                "line": None,
                "observed_angle_degrees": 0.0,
                "correction_angle_degrees": 0.0,
                "source_dimensions": [image_geometry.get("width"), image_geometry.get("height")] if image_geometry else None,
                "convention": "pil_counter_clockwise_positive"
            }
        }

    # Extract coordinates
    if isinstance(line, dict):
        x1, y1, x2, y2 = line["x1"], line["y1"], line["x2"], line["y2"]
    elif isinstance(line, (list, tuple)) and len(line) == 4:
        x1, y1, x2, y2 = line[0], line[1], line[2], line[3]
    else:
        raise ValueError(f"Invalid line format: {line}")

    obs_deg, corr_deg = compute_line_angle(x1, y1, x2, y2)

    return {
        "contract_version": 1,
        "angle_degrees": round(corr_deg, 4),
        "confidence": 1.0,
        "method": options.get("method", "manual_horizontal_edge_line"),
        "needs_manual_review": False,
        "diagnostics": {
            "status": "ACCEPTED",
            "line": {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)},
            "observed_angle_degrees": round(obs_deg, 4),
            "correction_angle_degrees": round(corr_deg, 4),
            "edge_used": options.get("edge_used", "top_or_bottom"),
            "source_dimensions": [image_geometry.get("width"), image_geometry.get("height")] if image_geometry else None,
            "convention": "pil_counter_clockwise_positive"
        }
    }


def apply_plate_orientation(
    source_image: Union[str, Any],
    orientation_result: Dict[str, Any],
    output_path: Optional[str] = None,
    resample_filter: int = None
) -> Any:
    """
    Applies orientation rotation to source image and saves to output_path non-destructively.
    If source_image is a file path and output_path is given, saves the rotated image and returns output_path.
    If angle_degrees is 0.0 (or SKIPPED), copies source or returns unchanged.
    """
    angle = orientation_result.get("angle_degrees", 0.0)

    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for apply_plate_orientation")

    if isinstance(source_image, str):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' does not exist")
        
        # Non-destructive: if 0 degree rotation and output specified, simply copy
        if abs(angle) < 1e-5 and output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(source_image, output_path)
            return output_path

        with Image.open(source_image) as img:
            filter_mode = resample_filter if resample_filter is not None else Image.Resampling.BICUBIC
            rotated = img.rotate(angle, resample=filter_mode, expand=False)
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                rotated.save(output_path)
                return output_path
            return rotated
    else:
        # source_image is already a PIL Image
        img = source_image
        if abs(angle) < 1e-5:
            return img.copy()
        filter_mode = resample_filter if resample_filter is not None else Image.Resampling.BICUBIC
        rotated = img.rotate(angle, resample=filter_mode, expand=False)
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            rotated.save(output_path)
            return output_path
        return rotated

