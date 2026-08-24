import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from tools.grid_coordinates import spot_list as grid_asset_spot_list
except ModuleNotFoundError:
    from grid_coordinates import spot_list as grid_asset_spot_list

try:
    import numpy as np
    from PIL import Image
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


DEFAULT_PRESETS = {
    "background_aware_linear": {
        "method": "background_aware_linear",
        "bg_percentile": 10.0,
        "fg_percentile": 99.0,
        "gamma": 1.0,
        "description": "Uses outside-grid background median/10th-pct as black point and inside-grid 99th-pct as white point"
    },
    "gamma_boost": {
        "method": "background_aware_linear",
        "bg_percentile": 15.0,
        "fg_percentile": 98.0,
        "gamma": 0.8,
        "description": "Background stretch with gamma boost for faint colonies"
    }
}


def _output_parent(path: str) -> str:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    return parent


def _preset_config(preset: Optional[Union[str, Dict[str, Any]]]) -> tuple[str, Dict[str, Any]]:
    if preset is None:
        return "background_aware_linear", dict(DEFAULT_PRESETS["background_aware_linear"])
    if isinstance(preset, str):
        if preset not in DEFAULT_PRESETS:
            raise ValueError(f"Unknown visibility preset: {preset}")
        return preset, dict(DEFAULT_PRESETS[preset])
    if isinstance(preset, dict):
        name = str(preset.get("name", "custom_preset"))
        config = dict(preset)
        method = config.get("method", "background_aware_linear")
        if method != "background_aware_linear":
            raise ValueError(f"Unsupported visibility method: {method}")
        return name, config
    raise TypeError("preset must be a known name, mapping, or None")

def calculate_grid_roi(
    grid_coordinates: Union[List[Tuple[float, float]], Dict[str, Any]],
    padding: float = 20.0,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> Dict[str, float]:
    """
    Computes bounding box of all spot coordinates with optional padding.
    """
    if isinstance(grid_coordinates, dict) and grid_coordinates.get("asset_type") == "GridCoordinateAsset":
        grid_coordinates = grid_asset_spot_list(grid_coordinates)

    if not grid_coordinates:
        raise ValueError("grid_coordinates must be a non-empty list of (x, y) coordinates")

    xs = [pt[0] for pt in grid_coordinates]
    ys = [pt[1] for pt in grid_coordinates]

    min_x = max(0.0, min(xs) - padding)
    min_y = max(0.0, min(ys) - padding)
    max_x = max(xs) + padding
    max_y = max(ys) + padding

    if max_width:
        max_x = min(float(max_width), max_x)
    if max_height:
        max_y = min(float(max_height), max_y)

    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x,
        "height": max_y - min_y,
        "left": min_x,
        "top": min_y,
        "right": max_x,
        "bottom": max_y
    }


def compute_visibility_statistics(
    image_array: Any,
    grid_roi: Dict[str, float],
    margin: float = 50.0
) -> Dict[str, float]:
    """
    Computes robust background and foreground statistics:
    - Inside-grid: pixels inside grid_roi
    - Outside-grid: background border band around grid_roi (clipped to image bounds)
    """
    h, w = image_array.shape[:2]

    gx1 = int(max(0, grid_roi["left"]))
    gy1 = int(max(0, grid_roi["top"]))
    gx2 = int(min(w, grid_roi["right"]))
    gy2 = int(min(h, grid_roi["bottom"]))

    inside_pixels = image_array[gy1:gy2, gx1:gx2]
    if inside_pixels.size == 0:
        raise ValueError("Accepted grid ROI does not overlap the source image.")

    # Create mask for outside-grid border
    bx1 = int(max(0, gx1 - margin))
    by1 = int(max(0, gy1 - margin))
    bx2 = int(min(w, gx2 + margin))
    by2 = int(min(h, gy2 + margin))

    outer_box = image_array[by1:by2, bx1:bx2]
    # Mask out the grid center
    mask = np.ones((by2 - by1, bx2 - bx1), dtype=bool)
    in_oy1 = gy1 - by1
    in_oy2 = gy2 - by1
    in_ox1 = gx1 - bx1
    in_ox2 = gx2 - bx1
    mask[in_oy1:in_oy2, in_ox1:in_ox2] = False

    outside_pixels = outer_box[mask]
    if len(outside_pixels) == 0:
        outside_pixels = image_array

    return {
        "bg_p10": float(np.percentile(outside_pixels, 10)),
        "bg_median": float(np.median(outside_pixels)),
        "fg_p98": float(np.percentile(inside_pixels, 98)),
        "fg_p99": float(np.percentile(inside_pixels, 99)),
        "inside_mean": float(np.mean(inside_pixels)),
        "outside_mean": float(np.mean(outside_pixels))
    }


def apply_display_transform(
    img_array: Any,
    black_point: float,
    white_point: float,
    gamma: float = 1.0
) -> Any:
    """
    Applies linear stretch and gamma curve to entire image array.
    """
    if white_point <= black_point:
        white_point = black_point + 1.0

    norm = (img_array.astype(np.float32) - black_point) / (white_point - black_point)
    norm = np.clip(norm, 0.0, 1.0)

    if abs(gamma - 1.0) > 1e-4 and gamma > 0:
        norm = np.power(norm, gamma)

    out = (norm * 255.0).astype(np.uint8)
    return out


def adjust_plate_visibility(
    source_image: Union[str, Any],
    grid_coordinates: Union[List[Tuple[float, float]], Dict[str, Any]],
    preset: Optional[Union[str, Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculates visibility adjustment parameters from grid ROI and outside-grid background.

    Returns AdjustmentResult dict.
    """
    options = options or {}
    image_uid = options.get("image_uid", "unknown_image")
    status = options.get("status", "PROPOSED")  # PROPOSED | ACCEPTED | MANUAL_REVIEW | SKIPPED
    if status not in {"PROPOSED", "ACCEPTED", "MANUAL_REVIEW", "SKIPPED"}:
        raise ValueError(f"Unsupported visibility status: {status}")
    needs_manual = (status == "MANUAL_REVIEW") or options.get("needs_manual_review", False)
    preset_name, preset_dict = _preset_config(preset)

    # If skipped
    if status == "SKIPPED":
        return {
            "contract_version": 1,
            "image_uid": str(image_uid),
            "preset_name": preset_name,
            "method": preset_dict.get("method", "background_aware_linear"),
            "status": "SKIPPED",
            "needs_manual_review": False,
            "parameters": {},
            "grid_roi": None,
            "statistics": {},
            "output_path": options.get("output_path"),
            "source_image_ref": options.get("source_image_ref") or (str(source_image) if isinstance(source_image, (str, Path)) else None),
            "grid_asset_id": grid_coordinates.get("asset_id") if isinstance(grid_coordinates, dict) else None,
            "output_dimensions": None
        }

    # Load image if file path
    if isinstance(source_image, (str, Path)):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' not found")
        with Image.open(source_image) as img:
            arr = np.array(img.convert("L"))
            img_w, img_h = img.size
    else:
        # PIL Image or numpy array
        if hasattr(source_image, "convert"):
            arr = np.array(source_image.convert("L"))
            img_w, img_h = source_image.size
        else:
            arr = source_image
            img_h, img_w = arr.shape[:2]

    grid_roi = calculate_grid_roi(grid_coordinates, padding=20.0, max_width=img_w, max_height=img_h)
    stats = compute_visibility_statistics(arr, grid_roi, margin=50.0)

    bg_p = preset_dict.get("bg_percentile", 10.0)
    fg_p = preset_dict.get("fg_percentile", 99.0)
    gamma = preset_dict.get("gamma", 1.0)

    black_point = stats["bg_p10"] if bg_p <= 10.0 else stats["bg_median"]
    white_point = stats["fg_p99"] if fg_p >= 99.0 else stats["fg_p98"]

    return {
        "contract_version": 1,
        "image_uid": str(image_uid),
        "preset_name": preset_name,
        "method": preset_dict.get("method", "background_aware_linear"),
        "status": status,
        "needs_manual_review": needs_manual,
        "manual_review_reason": options.get("manual_review_reason") if needs_manual else None,
        "parameters": {
            "black_point": round(float(black_point), 2),
            "white_point": round(float(white_point), 2),
            "gamma": float(gamma)
        },
        "grid_roi": grid_roi,
        "statistics": stats,
        "output_path": options.get("output_path"),
        "source_image_ref": options.get("source_image_ref") or (str(source_image) if isinstance(source_image, (str, Path)) else None),
        "grid_asset_id": grid_coordinates.get("asset_id") if isinstance(grid_coordinates, dict) else None,
        "output_dimensions": [img_w, img_h]
    }


def apply_visibility_adjustment(
    source_image: Union[str, Any],
    adjustment_result: Dict[str, Any],
    output_path: Optional[str] = None
) -> Any:
    """
    Applies visibility adjustment to the entire source image non-destructively.
    """
    if not DEPS_AVAILABLE:
        raise RuntimeError("Pillow and numpy are required for apply_visibility_adjustment")

    status = adjustment_result.get("status", "PROPOSED")
    if output_path and status not in {"ACCEPTED", "SKIPPED"}:
        raise ValueError("A proposed visibility adjustment cannot be written before acceptance.")
    params = adjustment_result.get("parameters", {})

    if isinstance(source_image, (str, Path)):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' does not exist")

        if status == "SKIPPED" or not params:
            if output_path:
                _output_parent(output_path)
                shutil.copy2(source_image, output_path)
                return output_path
            return Image.open(source_image)

        with Image.open(source_image) as img:
            arr = np.array(img)
            bp = params.get("black_point", 0.0)
            wp = params.get("white_point", 255.0)
            gamma = params.get("gamma", 1.0)
            adjusted_arr = apply_display_transform(arr, bp, wp, gamma)
            out_img = Image.fromarray(adjusted_arr)

            if output_path:
                _output_parent(output_path)
                out_img.save(output_path)
                return output_path
            return out_img
    else:
        arr = np.array(source_image)
        if status == "SKIPPED" or not params:
            return source_image
        bp = params.get("black_point", 0.0)
        wp = params.get("white_point", 255.0)
        gamma = params.get("gamma", 1.0)
        adjusted_arr = apply_display_transform(arr, bp, wp, gamma)
        out_img = Image.fromarray(adjusted_arr)
        if output_path:
            _output_parent(output_path)
            out_img.save(output_path)
            return output_path
        return out_img


class ReviewQueue:
    """
    Manages a persistent JSON review queue for images marked for manual adjustment.
    """
    def __init__(self, queue_file_path: str):
        self.queue_file_path = queue_file_path
        self.entries = []
        self.load()

    def load(self):
        if os.path.exists(self.queue_file_path):
            try:
                with open(self.queue_file_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception:
                self.entries = []
        else:
            self.entries = []

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.queue_file_path)), exist_ok=True)
        with open(self.queue_file_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)

    def add_entry(self, image_uid: str, source_path: str, reason: Optional[str] = None, preset: Optional[str] = None):
        entry = {
            "image_uid": str(image_uid),
            "source_path": source_path,
            "preset": preset or "default",
            "reason": reason or "Flagged by user for manual review",
            "reviewed": False
        }
        self.entries.append(entry)
        self.save()

    def get_pending(self) -> List[Dict[str, Any]]:
        return [e for e in self.entries if not e.get("reviewed", False)]

    def mark_reviewed(self, image_uid: str):
        for e in self.entries:
            if e.get("image_uid") == str(image_uid):
                e["reviewed"] = True
        self.save()


def write_visibility_result(result: Dict[str, Any], result_path: str) -> str:
    """Atomically write accepted adjustment metadata beside its output."""
    if result.get("status") != "ACCEPTED":
        raise ValueError("Only accepted visibility results may be written.")
    parent = _output_parent(result_path)
    fd, temporary = tempfile.mkstemp(prefix=".visibility-", suffix=".tmp", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, result_path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return result_path