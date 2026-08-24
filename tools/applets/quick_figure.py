from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from tools.applets.annotation import render_plate_annotation
from tools.applets.plate_orientation import (
    apply_plate_orientation,
    capture_plate_orientation,
)

POSITION_ALIASES = ("pos", "position", "well", "column", "col")
STRAIN_ALIASES = ("strain", "labels strain", "well label", "label")
METADATA_ALIASES = {
    "date": ("date",),
    "plate": ("plate", "plate number"),
    "condition": ("condition",),
    "session": ("session",),
    "media": ("media",),
    "figure_description": ("figure description", "figure_description", "description"),
}


def _key(value: str) -> str:
    return " ".join(str(value).strip().casefold().replace("_", " ").split())


def load_quick_csv(path: str | Path) -> dict[str, Any]:
    """Load a minimal or V10-compatible 1xN label CSV without project verification."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"CSV does not exist: {source}")
    sample = source.read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",;\t")
    rows = list(csv.DictReader(sample.splitlines(), dialect=dialect))
    if not rows:
        raise ValueError("CSV must contain at least one data row.")
    headers = {_key(header): header for header in (rows[0].keys() if rows else [])}
    strain_header = next(
        (headers[name] for name in STRAIN_ALIASES if name in headers), None
    )
    if strain_header is None:
        raise ValueError("CSV requires Strain or labels_strain.")
    pos_header = next(
        (headers[name] for name in POSITION_ALIASES if name in headers), None
    )
    labels = []
    metadata: dict[str, str] = {}
    used_positions = set()
    for index, row in enumerate(rows, 1):
        label = str(row.get(strain_header) or "").strip()
        if not label:
            raise ValueError(f"CSV row {index + 1} has a missing strain label.")
        raw_pos = (
            str(row.get(pos_header) or index).strip() if pos_header else str(index)
        )
        clean_pos = (
            raw_pos.casefold().lstrip("r").replace("c", "")
            if raw_pos.casefold().startswith("r1c")
            else raw_pos
        )
        try:
            position = int(clean_pos)
        except ValueError as exc:
            raise ValueError(
                f"CSV row {index + 1} has an invalid well position: {raw_pos}"
            ) from exc
        if position < 1 or position in used_positions:
            raise ValueError("Well positions must be positive and unique.")
        used_positions.add(position)
        labels.append({"pos": position, "label": label})
        for field, aliases in METADATA_ALIASES.items():
            header = next((headers[name] for name in aliases if name in headers), None)
            value = str(row.get(header) or "").strip() if header else ""
            if value and field not in metadata:
                metadata[field] = value
    labels.sort(key=lambda item: item["pos"])
    expected = list(range(1, len(labels) + 1))
    if [item["pos"] for item in labels] != expected:
        raise ValueError("Quick Figure wells must be contiguous positions 1..N.")
    return {"source_csv": str(source.resolve()), "labels": labels, "metadata": metadata}


def quick_layout(
    labels: list[dict[str, Any]], layout_id: str = "quick-1xn"
) -> dict[str, Any]:
    if not labels:
        raise ValueError("At least one well label is required.")
    return {
        "contract_version": 1,
        "layout_id": layout_id,
        "grid_rows": 1,
        "grid_cols": len(labels),
        "vertical_labels": [{"pos": 1, "label": ""}],
        "strain_bands": [
            {
                "order": 1,
                "row_start": 1,
                "row_end": 1,
                "local_grid_cols": len(labels),
                "labels": labels,
            }
        ],
    }


def register_quick_grid(
    image_ref: str | Path,
    image_size: tuple[int, int],
    first_center: tuple[float, float],
    last_center: tuple[float, float],
    columns: int,
) -> dict[str, Any]:
    """Create durable 1xN centers using two endpoints and explicit provenance."""
    width, height = (int(image_size[0]), int(image_size[1]))
    if width < 1 or height < 1 or columns < 1:
        raise ValueError("Image dimensions and column count must be positive.")
    points = (
        [first_center]
        if columns == 1
        else [
            (
                first_center[0]
                + (last_center[0] - first_center[0]) * index / (columns - 1),
                first_center[1]
                + (last_center[1] - first_center[1]) * index / (columns - 1),
            )
            for index in range(columns)
        ]
    )
    if any(not (0 <= x < width and 0 <= y < height) for x, y in points):
        raise ValueError("All registered well centers must be inside the image.")
    payload = {
        "contract_version": 1,
        "asset_type": "QuickGridAsset",
        "method": "two_endpoint_1xn_linear_v1",
        "image_ref": str(Path(image_ref).resolve()),
        "coordinate_system": {
            "origin": "top_left",
            "x_direction": "right",
            "y_direction": "down",
            "units": "pixels",
            "image_width": width,
            "image_height": height,
        },
        "grid": {"rows": 1, "columns": columns},
        "reference_points": {
            "r1c1": {"x": float(first_center[0]), "y": float(first_center[1])},
            f"r1c{columns}": {"x": float(last_center[0]), "y": float(last_center[1])},
        },
        "spots": [
            {
                "spot_id": f"r1c{index}",
                "row": 1,
                "column": index,
                "x": float(point[0]),
                "y": float(point[1]),
            }
            for index, point in enumerate(points, 1)
        ],
        "provenance": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "qc_status": "UNREVIEWED",
            "source": "quick_figure_manual_endpoints",
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["asset_id"] = "quick-grid-" + hashlib.sha256(canonical).hexdigest()[:16]
    return payload


def set_grid_qc(
    asset: dict[str, Any], accepted: bool, note: str = ""
) -> dict[str, Any]:
    result = json.loads(json.dumps(asset))
    result["provenance"]["qc_status"] = "ACCEPTED" if accepted else "FLAGGED"
    result["provenance"]["qc_note"] = str(note).strip()
    result["provenance"]["qc_at"] = datetime.now(timezone.utc).isoformat()
    return result


def save_quick_grid(asset: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asset, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def spot_map(asset: dict[str, Any]) -> dict[tuple[int, int], tuple[float, float]]:
    if asset.get("asset_type") != "QuickGridAsset":
        raise ValueError("Expected a QuickGridAsset.")
    return {
        (1, int(spot["column"])): (float(spot["x"]), float(spot["y"]))
        for spot in asset["spots"]
    }


def calculate_box_from_roi(
    left: float, top: float, right: float, bottom: float
) -> dict[str, int]:
    values = [float(left), float(top), float(right), float(bottom)]
    if (
        not all(math.isfinite(value) for value in values)
        or right <= left
        or bottom <= top
    ):
        raise ValueError(
            "ROI must have finite left < right and top < bottom coordinates."
        )
    return {"width": round(right - left), "height": round(bottom - top)}


def well_rectangles(
    asset: dict[str, Any], width: int, height: int
) -> list[dict[str, Any]]:
    if width < 1 or height < 1:
        raise ValueError("Crop width and height must be positive.")
    image_width = asset["coordinate_system"]["image_width"]
    image_height = asset["coordinate_system"]["image_height"]
    result = []
    for spot in asset["spots"]:
        left = round(spot["x"] - width / 2)
        top = round(spot["y"] - height / 2)
        box = (left, top, left + width, top + height)
        if left < 0 or top < 0 or box[2] > image_width or box[3] > image_height:
            raise ValueError(f"{spot['spot_id']} crop extends outside the image.")
        result.append(
            {"spot_id": spot["spot_id"], "column": spot["column"], "box": box}
        )
    return result


def align_image_to_edge(
    image: Image.Image,
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[Image.Image, dict[str, Any]]:
    """Align a dragged top/bottom edge using the production orientation convention."""
    result = capture_plate_orientation(
        (*start, *end),
        {"width": image.width, "height": image.height, "image_uid": "quick-figure"},
        {"accepted": True, "method": "quick_figure_manual_horizontal_edge_line"},
    )
    return apply_plate_orientation(image, result), result


def orient_image(image: Image.Image, operation: str) -> Image.Image:
    operations = {
        "none": lambda value: value.copy(),
        "rotate_90_cw": lambda value: value.transpose(Image.Transpose.ROTATE_270),
        "rotate_90_ccw": lambda value: value.transpose(Image.Transpose.ROTATE_90),
        "rotate_180": lambda value: value.transpose(Image.Transpose.ROTATE_180),
        "flip_horizontal": lambda value: value.transpose(
            Image.Transpose.FLIP_LEFT_RIGHT
        ),
        "flip_vertical": lambda value: value.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
    }
    try:
        return operations[operation](image)
    except KeyError as exc:
        raise ValueError(f"Unknown orientation operation: {operation}") from exc


def annotate_quick(
    source_image: str | Path | Image.Image,
    data: dict[str, Any],
    asset: dict[str, Any],
    preset: dict[str, Any] | None = None,
    labels_override: dict[str, str] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    layout = quick_layout(data["labels"])
    labels = {**data.get("metadata", {}), **(labels_override or {})}
    preset = {**(preset or {}), "vertical_visible": False}
    request = {
        "contract_version": 1,
        "image_uid": "quick-figure",
        "layout_id": layout["layout_id"],
        "labels": labels,
    }
    return render_plate_annotation(
        source_image, layout, spot_map(asset), request, preset, output_path
    )


def export_wells(
    source_image: str | Path | Image.Image,
    asset: dict[str, Any],
    labels: list[dict[str, Any]],
    width: int,
    height: int,
    output_root: str | Path,
) -> dict[str, Any]:
    rectangles = well_rectangles(asset, width, height)
    label_by_pos = {int(item["pos"]): str(item["label"]) for item in labels}
    if set(label_by_pos) != {item["column"] for item in rectangles}:
        raise ValueError("Labels and registered wells do not match.")
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    existing = [
        int(path.name.split("-")[-1])
        for path in root.glob("quick-wells-*")
        if path.is_dir() and path.name.split("-")[-1].isdigit()
    ]
    run = root / f"quick-wells-{max(existing, default=0) + 1:03d}"
    run.mkdir()
    image = (
        Image.open(source_image).convert("RGB")
        if isinstance(source_image, (str, Path))
        else source_image.convert("RGB")
    )
    outputs = []
    for item in rectangles:
        safe = (
            "".join(
                character if character.isalnum() or character in "-_ " else "_"
                for character in label_by_pos[item["column"]]
            ).strip()
            or item["spot_id"]
        )
        destination = run / f"{item['spot_id']}_{safe}.png"
        image.crop(item["box"]).save(destination)
        outputs.append(
            {
                "spot_id": item["spot_id"],
                "label": label_by_pos[item["column"]],
                "box": list(item["box"]),
                "path": str(destination.resolve()),
            }
        )
    manifest = {
        "contract_version": 1,
        "asset_type": "QuickWellExport",
        "grid_asset_id": asset["asset_id"],
        "crop_size": {"width": width, "height": height},
        "outputs": outputs,
    }
    save_quick_grid(manifest, run / "manifest.json")
    return manifest
