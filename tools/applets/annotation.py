import math
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from tools.grid_coordinates import spot_mapping as grid_asset_spot_mapping
except ModuleNotFoundError:
    from grid_coordinates import spot_mapping as grid_asset_spot_mapping

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

    preset = preset or DEFAULT_ANNOTATION_PRESET
    req = annotation_request or {}

    # Load source image
    if isinstance(source_image, str):
        if not os.path.exists(source_image):
            raise FileNotFoundError(f"Source image '{source_image}' not found")
        base_img = Image.open(source_image).convert("RGB")
    else:
        base_img = source_image.convert("RGB") if hasattr(source_image, "convert") else Image.fromarray(source_image)

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
            draw.text((v["x"], v["y"]), txt, fill=color, font=vert_font)
        else:
            txt_img = render_rotated_text_image(txt, vert_font, rot, fill=color)
            canvas.paste(txt_img, (int(v["x"]), int(v["y"])), txt_img)

    # 3. Render Strain column labels (rotated 90 deg clockwise by default)
    for s in pos_data["strain_placements"]:
        txt = str(s["label"])
        rot = s["rotation"]
        if rot == 0:
            draw.text((s["x"], s["y"]), txt, fill=color, font=strain_font)
        else:
            txt_img = render_rotated_text_image(txt, strain_font, rot, fill=color)
            canvas.paste(txt_img, (int(s["x"]), int(s["y"])), txt_img)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        canvas.save(output_path)

    return {
        "contract_version": 1,
        "image_uid": req.get("image_uid", "unknown"),
        "layout_id": plate_layout.get("layout_id", "1"),
        "status": "RENDERED",
        "output_dimensions": [canvas_w, canvas_h],
        "output_path": output_path,
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
    """
    Composes a structured matrix grid from individual crop images (with mixed crop tier support).

    crop_items: List of dicts:
      [{'image': Image | str, 'row': int, 'col': int, 'strain': str, 'condition': str, 'tier': 'top'|'low'}, ...]
    matrix_layout:
      {'rows': ['WT', 'MutantA'], 'cols': ['0h', '24h', '48h'], 'tile_size': (120, 120), 'padding': 10}
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for compose_matrix")

    row_keys = matrix_layout.get("rows", [])
    col_keys = matrix_layout.get("cols", [])
    tile_w, tile_h = matrix_layout.get("tile_size", (120, 120))
    pad = matrix_layout.get("padding", 10)
    margin_top = 40
    margin_left = 100

    n_rows = len(row_keys)
    n_cols = len(col_keys)

    total_w = margin_left + n_cols * (tile_w + pad) + pad
    total_h = margin_top + n_rows * (tile_h + pad) + pad

    matrix_img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(matrix_img)
    font = _get_font(16)

    # Draw column headers
    for c_idx, col_name in enumerate(col_keys):
        x = margin_left + c_idx * (tile_w + pad) + pad
        y = 10
        draw.text((x, y), str(col_name), fill=(0, 0, 0), font=font)

    # Draw row headers
    for r_idx, row_name in enumerate(row_keys):
        x = 10
        y = margin_top + r_idx * (tile_h + pad) + pad + (tile_h // 2) - 8
        draw.text((x, y), str(row_name), fill=(0, 0, 0), font=font)

    # Draw tiles
    for item in crop_items:
        r_name = item.get("strain") or item.get("row")
        c_name = item.get("condition") or item.get("col")

        if r_name in row_keys and c_name in col_keys:
            r_i = row_keys.index(r_name)
            c_i = col_keys.index(c_name)

            x = margin_left + c_i * (tile_w + pad) + pad
            y = margin_top + r_i * (tile_h + pad) + pad

            src = item.get("image")
            if isinstance(src, str):
                tile = Image.open(src).convert("RGB")
            elif hasattr(src, "convert"):
                tile = src.convert("RGB")
            else:
                tile = Image.fromarray(src).convert("RGB")

            tile = tile.resize((tile_w, tile_h), Image.Resampling.BILINEAR)
            matrix_img.paste(tile, (x, y))

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        matrix_img.save(output_path)

    return {
        "status": "COMPOSED",
        "output_dimensions": [total_w, total_h],
        "output_path": output_path,
        "rows": row_keys,
        "cols": col_keys,
        "tile_count": len(crop_items)
    }
