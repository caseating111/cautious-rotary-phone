import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from tools.applets.plate_layout import validate_plate_layout
    from tools.grid_coordinates import spot_mapping as grid_asset_spot_mapping
except ModuleNotFoundError:
    from grid_coordinates import spot_mapping as grid_asset_spot_mapping
    from plate_layout import validate_plate_layout

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


DEFAULT_ANNOTATION_PRESET = {
    "name": "standard_90deg_strain",
    "header_font_size": 24,
    "strain_font_size": 18,
    "vertical_font_size": 18,
    "text_color": (0, 0, 0),
    "background_color": (255, 255, 255),
    "strain_rotation_degrees": 90.0,  # 90 deg clockwise
    "vertical_rotation_degrees": 0.0,
    "strain_offset_y": -20.0,
    "vertical_offset_x": -30.0,
    "canvas_padding": {
        "top": 80,
        "bottom": 30,
        "left": 80,
        "right": 30
    }
}


def validate_annotation_request(request: Dict[str, Any]) -> None:
    required = ("contract_version", "image_uid", "layout_id", "labels")
    if not isinstance(request, dict) or any(not request.get(key) for key in required):
        raise ValueError("annotation_request requires contract_version, image_uid, layout_id, and labels")
    if request.get("contract_version") != 1 or not isinstance(request["labels"], dict):
        raise ValueError("Unsupported annotation_request contract")


def _atomic_json(value: Dict[str, Any], path: str) -> str:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".annotation-", suffix=".tmp", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path

def _get_font(size: int = 18):
    if not PIL_AVAILABLE:
        return None
    try:
        # Standard system fonts or default
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.load_default()
        except Exception:
            return None


def render_rotated_text_image(
    text: str,
    font: Any,
    angle_degrees: float = 0.0,
    fill: Tuple[int, int, int] = (0, 0, 0)
) -> Any:
    """
    Renders text onto a tight RGBA canvas and rotates it by angle_degrees.
    Angle convention: positive angle rotates clockwise.
    """
    if not PIL_AVAILABLE:
        return None

    # Dummy draw to measure text size
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(dummy_img)
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])
    except Exception:
        text_w = len(text) * 10
        text_h = 16

    pad = 4
    txt_img = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0, 0, 0, 0))
    d_txt = ImageDraw.Draw(txt_img)
    d_txt.text((pad, pad), text, fill=fill, font=font)

    if abs(angle_degrees) > 1e-4:
        # PIL rotate rotates counter-clockwise for positive degrees, so pass -angle_degrees for clockwise
        rotated = txt_img.rotate(-angle_degrees, expand=True, resample=Image.Resampling.BICUBIC)
        return rotated
    return txt_img


def _record_rendered_box(record, box, canvas_size, warnings, label_class):
    left, top, right, bottom = (int(value) for value in box)
    record["rendered_box"] = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
    }
    width, height = canvas_size
    if left < 0 or top < 0 or right > width or bottom > height:
        warnings.append(
            f"{label_class} label {record.get('label')!r} extends outside the annotation canvas."
        )

def derive_annotation_positions(
    plate_layout: Dict[str, Any],
    grid_coordinates: Union[Dict[Tuple[int, int], Tuple[float, float]], Dict[str, Any]],
    preset: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Derives deterministic screen coordinates for every annotation label:
    - Vertical labels aligned to row Y coordinates
    - Strain labels aligned to column X coordinates above each band

    grid_coordinates: mapping of (row, col) -> (x, y) spot center
    """
    if isinstance(grid_coordinates, dict) and grid_coordinates.get("asset_type") == "GridCoordinateAsset":
        grid_coordinates = grid_asset_spot_mapping(grid_coordinates)

    preset = preset or DEFAULT_ANNOTATION_PRESET
    pad_top = preset.get("canvas_padding", {}).get("top", 0)
    pad_left = preset.get("canvas_padding", {}).get("left", 0)

    rows = plate_layout.get("grid_rows", 8)
    cols = plate_layout.get("grid_cols", 12)

    # Compute column average X positions
    col_x = {}
    for c in range(1, cols + 1):
        xs = [grid_coordinates[(r, c)][0] for r in range(1, rows + 1) if (r, c) in grid_coordinates]
        col_x[c] = (sum(xs) / len(xs)) if xs else (c * 50.0)

    # Compute row average Y positions
    row_y = {}
    for r in range(1, rows + 1):
        ys = [grid_coordinates[(r, c)][1] for c in range(1, cols + 1) if (r, c) in grid_coordinates]
        row_y[r] = (sum(ys) / len(ys)) if ys else (r * 50.0)

    # Derive vertical label positions
    vertical_placements = []
    for v in plate_layout.get("vertical_labels", []):
        r_pos = v["pos"]
        y_pos = row_y.get(r_pos, r_pos * 50.0) + pad_top
        # Placed to the left of column 1
        min_x = min(col_x.values()) + pad_left
        x_pos = min_x + preset.get("vertical_offset_x", -30.0)
        vertical_placements.append({
            "pos": r_pos,
            "label": v["label"],
            "x": x_pos,
            "y": y_pos,
            "rotation": preset.get("vertical_rotation_degrees", 0.0)
        })

    # Derive strain label positions per band
    strain_placements = []
    for band in plate_layout.get("strain_bands", []):
        order = band.get("order", 1)
        r_start = band.get("row_start", 1)
        band_top_y = row_y.get(r_start, 50.0) + pad_top
        y_pos = band_top_y + preset.get("strain_offset_y", -20.0)

        for s in band.get("labels", []):
            c_pos = s["pos"]
            x_pos = col_x.get(c_pos, c_pos * 50.0) + pad_left
            strain_placements.append({
                "order": order,
                "pos": c_pos,
                "label": s["label"],
                "x": x_pos,
                "y": y_pos,
                "rotation": preset.get("strain_rotation_degrees", 90.0)
            })

    return {
        "vertical_placements": vertical_placements,
        "strain_placements": strain_placements,
        "col_x": col_x,
        "row_y": row_y
    }


def render_plate_annotation(
    source_image: Union[str, Any],
    plate_layout: Dict[str, Any],
    grid_coordinates: Union[Dict[Tuple[int, int], Tuple[float, float]], List[Tuple[float, float]]],
    annotation_request: Optional[Dict[str, Any]] = None,
    preset: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Renders automatic annotations onto source_image using PlateLayout and Grid coordinates.
    Non-destructive: writes to output_path or returns result.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for render_plate_annotation")

    validate_plate_layout(plate_layout)
    requested_preset = preset or {}
    preset = dict(DEFAULT_ANNOTATION_PRESET)
    preset.update(requested_preset)
    preset["canvas_padding"] = {
        **DEFAULT_ANNOTATION_PRESET["canvas_padding"],
        **requested_preset.get("canvas_padding", {}),
    }
    req = annotation_request or {}
    validate_annotation_request(req)
    if req["layout_id"] != str(plate_layout.get("layout_id", "")):
        raise ValueError("Annotation request layout_id does not match PlateLayout.")
    request_options = req.get("options", {})
    if "strain_text_rotation_degrees" in request_options:
        preset["strain_rotation_degrees"] = request_options["strain_text_rotation_degrees"]
    if "vertical_text_rotation_degrees" in request_options:
        preset["vertical_rotation_degrees"] = request_options["vertical_text_rotation_degrees"]
    if isinstance(grid_coordinates, dict) and grid_coordinates.get("asset_type") == "GridCoordinateAsset":
        asset_uid = grid_coordinates.get("image_uid")
        if asset_uid not in {None, "", req["image_uid"]}:
            raise ValueError("Grid asset belongs to a different Image UID.")
        grid = grid_coordinates.get("grid", {})
        if (grid.get("rows"), grid.get("columns")) != (
            plate_layout.get("grid_rows"),
            plate_layout.get("grid_cols"),
        ):
            raise ValueError("Grid asset dimensions do not match PlateLayout.")

    # Load source image
    if isinstance(source_image, (str, Path)):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' not found")
        base_img = Image.open(source_image).convert("RGB")
    else:
        base_img = source_image.convert("RGB") if hasattr(source_image, "convert") else Image.fromarray(source_image)

    if isinstance(grid_coordinates, dict) and grid_coordinates.get("asset_type") == "GridCoordinateAsset":
        space = grid_coordinates.get("coordinate_space", {})
        if (space.get("image_width"), space.get("image_height")) != base_img.size:
            raise ValueError("Grid asset coordinate-space dimensions do not match source image.")

    # Convert list of coordinates to (r, c) dict if needed
    rows = plate_layout.get("grid_rows", 8)
    cols = plate_layout.get("grid_cols", 12)

    if isinstance(grid_coordinates, dict) and grid_coordinates.get("asset_type") == "GridCoordinateAsset":
        grid_map = grid_asset_spot_mapping(grid_coordinates)
    elif isinstance(grid_coordinates, list):
        # Map sequential list to (r, c)
        grid_map = {}
        idx = 0
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                if idx < len(grid_coordinates):
                    grid_map[(r, c)] = grid_coordinates[idx]
                    idx += 1
                else:
                    grid_map[(r, c)] = (float(c * 60), float(r * 60))
    else:
        grid_map = grid_coordinates

    pad = preset.get("canvas_padding", {"top": 80, "bottom": 30, "left": 80, "right": 30})
    canvas_w = base_img.width + pad["left"] + pad["right"]
    canvas_h = base_img.height + pad["top"] + pad["bottom"]

    canvas = Image.new("RGB", (canvas_w, canvas_h), color=preset.get("background_color", (255, 255, 255)))
    canvas.paste(base_img, (pad["left"], pad["top"]))

    draw = ImageDraw.Draw(canvas)
    hdr_font = _get_font(preset.get("header_font_size", 24))
    strain_font = _get_font(preset.get("strain_font_size", 18))
    vert_font = _get_font(preset.get("vertical_font_size", 18))
    color = preset.get("text_color", (0, 0, 0))

    # Derive positions
    pos_data = derive_annotation_positions(plate_layout, grid_map, preset)

    warnings = []

    # 1. Render Header labels (Date, Condition, Session, Plate)
    labels = req.get("labels", {})
    header_parts = []
    if labels.get("date"):
        header_parts.append(f"Date: {labels['date']}")
    if labels.get("condition"):
        header_parts.append(f"Cond: {labels['condition']}")
    if labels.get("session"):
        header_parts.append(f"Session: {labels['session']}")
    if labels.get("plate"):
        header_parts.append(f"Plate: {labels['plate']}")

    if header_parts:
        hdr_text = " | ".join(header_parts)
        draw.text((pad["left"], 15), hdr_text, fill=color, font=hdr_font)

    # 2. Render Vertical row labels
    for v in pos_data["vertical_placements"]:
        txt = str(v["label"])
        rot = v["rotation"]
        if rot == 0:
            position = (v["x"], v["y"])
            draw.text(position, txt, fill=color, font=vert_font)
            box = draw.textbbox(position, txt, font=vert_font)
        else:
            txt_img = render_rotated_text_image(txt, vert_font, rot, fill=color)
            position = (int(v["x"]), int(v["y"]))
            canvas.paste(txt_img, position, txt_img)
            box = (*position, position[0] + txt_img.width, position[1] + txt_img.height)
        _record_rendered_box(v, box, canvas.size, warnings, "vertical")

    # 3. Render Strain column labels (rotated 90 deg clockwise by default)
    for s in pos_data["strain_placements"]:
        txt = str(s["label"])
        rot = s["rotation"]
        if rot == 0:
            position = (s["x"], s["y"])
            draw.text(position, txt, fill=color, font=strain_font)
            box = draw.textbbox(position, txt, font=strain_font)
        else:
            txt_img = render_rotated_text_image(txt, strain_font, rot, fill=color)
            position = (int(s["x"]), int(s["y"]))
            canvas.paste(txt_img, position, txt_img)
            box = (*position, position[0] + txt_img.width, position[1] + txt_img.height)
        _record_rendered_box(s, box, canvas.size, warnings, "strain")

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        canvas.save(output_path)

    return {
        "contract_version": 1,
        "image_uid": req.get("image_uid", "unknown"),
        "layout_id": plate_layout.get("layout_id", "1"),
        "status": "ACCEPTED" if output_path else "PROPOSED",
        "output_dimensions": [canvas_w, canvas_h],
        "output_path": output_path,
        "source_image_ref": req.get("source_image_ref") or (str(source_image) if isinstance(source_image, (str, Path)) else None),
        "grid_asset_id": grid_coordinates.get("asset_id") if isinstance(grid_coordinates, dict) else None,
        "warnings": warnings,
        "placements": pos_data,
        "preview_image": canvas if output_path is None else None,
        "preset_used": preset.get("name", "custom"),
        "rendered_labels": {
            "header": header_parts,
            "vertical_count": len(pos_data["vertical_placements"]),
            "strain_count": len(pos_data["strain_placements"])
        }
    }


def compose_matrix(
    crop_items: List[Dict[str, Any]],
    matrix_layout: Dict[str, Any],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Compose a validated mixed-tier crop matrix."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for compose_matrix")
    if not isinstance(matrix_layout, dict):
        raise ValueError("matrix_layout must be an object.")
    row_keys = matrix_layout.get("rows")
    col_keys = matrix_layout.get("cols")
    if not isinstance(row_keys, list) or not row_keys or any(not str(v).strip() for v in row_keys):
        raise ValueError("matrix_layout rows must be non-empty keys.")
    if not isinstance(col_keys, list) or not col_keys or any(not str(v).strip() for v in col_keys):
        raise ValueError("matrix_layout cols must be non-empty keys.")
    if len({str(v) for v in row_keys}) != len(row_keys) or len({str(v) for v in col_keys}) != len(col_keys):
        raise ValueError("matrix_layout rows and cols must be unique.")
    tile_size = matrix_layout.get("tile_size", (120, 120))
    if not isinstance(tile_size, (tuple, list)) or len(tile_size) != 2:
        raise ValueError("tile_size must contain width and height.")
    tile_w, tile_h = (int(tile_size[0]), int(tile_size[1]))
    pad = int(matrix_layout.get("padding", 10))
    if tile_w <= 0 or tile_h <= 0 or pad < 0:
        raise ValueError("tile_size must be positive and padding cannot be negative.")
    if not isinstance(crop_items, list):
        raise ValueError("crop_items must be a list.")
    row_lookup = {str(v): v for v in row_keys}
    col_lookup = {str(v): v for v in col_keys}
    validated = []
    occupied = set()
    for item in crop_items:
        if not isinstance(item, dict):
            raise ValueError("Each crop item must be an object.")
        tier = str(item.get("tier", "")).strip().casefold()
        if tier not in {"top", "low"}:
            raise ValueError("Each crop item tier must be Top or Low.")
        r_name = item.get("strain") if item.get("strain") is not None else item.get("row")
        c_name = item.get("condition") if item.get("condition") is not None else item.get("col")
        r_name, c_name = str(r_name), str(c_name)
        if r_name not in row_lookup or c_name not in col_lookup:
            raise ValueError("Crop item row/column is not present in matrix layout.")
        cell = (r_name, c_name)
        if cell in occupied:
            raise ValueError("Each matrix cell may contain only one crop item.")
        occupied.add(cell)
        src = item.get("image")
        if isinstance(src, (str, Path)):
            if not Path(src).is_file():
                raise FileNotFoundError(f"Crop source does not exist: {src}")
            with Image.open(src) as source_image:
                loaded = source_image.convert("RGB")
        elif hasattr(src, "convert"):
            loaded = src.convert("RGB")
        else:
            raise ValueError("Crop item image must be an existing path or PIL image.")
        validated.append((r_name, c_name, loaded))
    margin_top, margin_left = 40, 100
    total_w = margin_left + len(col_keys) * (tile_w + pad) + pad
    total_h = margin_top + len(row_keys) * (tile_h + pad) + pad
    matrix_img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(matrix_img)
    font = _get_font(16)
    for c_idx, col_name in enumerate(col_keys):
        draw.text((margin_left + c_idx * (tile_w + pad) + pad, 10), str(col_name), fill=(0, 0, 0), font=font)
    for r_idx, row_name in enumerate(row_keys):
        y = margin_top + r_idx * (tile_h + pad) + pad + (tile_h // 2) - 8
        draw.text((10, y), str(row_name), fill=(0, 0, 0), font=font)
    row_index = {str(v): i for i, v in enumerate(row_keys)}
    col_index = {str(v): i for i, v in enumerate(col_keys)}
    for r_name, c_name, tile in validated:
        x = margin_left + col_index[c_name] * (tile_w + pad) + pad
        y = margin_top + row_index[r_name] * (tile_h + pad) + pad
        matrix_img.paste(tile.resize((tile_w, tile_h), Image.Resampling.BILINEAR), (x, y))
    published_path = None
    if output_path:
        destination = Path(output_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".matrix-", suffix=destination.suffix or ".png", dir=str(destination.parent))
        os.close(fd)
        try:
            matrix_img.save(temporary)
            os.replace(temporary, destination)
            published_path = str(destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {
        "status": "COMPOSED" if output_path else "PREVIEW",
        "output_dimensions": [total_w, total_h],
        "output_path": published_path,
        "rows": row_keys,
        "cols": col_keys,
        "tile_count": len(validated),
        "preview_image": matrix_img if output_path is None else None,
    }


def preview_plate_annotation(source_image: Union[str, Any], plate_layout: Dict[str, Any], grid_coordinates: Union[Dict[Tuple[int, int], Tuple[float, float]], List[Tuple[float, float]], Dict[str, Any]], annotation_request: Dict[str, Any], preset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Render an in-memory preview without writing source or output files."""
    result = render_plate_annotation(source_image, plate_layout, grid_coordinates, annotation_request, preset, None)
    if result.get("preview_image") is None:
        raise RuntimeError("Annotation preview did not produce an in-memory image")
    return result


def write_annotation_result(result: Dict[str, Any], result_path: str) -> str:
    """Atomically write accepted annotation metadata."""
    return _atomic_json(result, result_path)
