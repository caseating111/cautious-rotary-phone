from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
METHOD = "four_point_r1_r5_bilinear_v1"
COORDINATE_SPACE = "source_image_pixels"
REFERENCE_NAMES = ("r1c1", "r1clast", "r5c1", "r5clast")
HANDOFF_FIELDS = (
    "folder",
    "filename",
    "experiment",
    "set",
    "type",
    "image_uid",
    "run_label",
    "image_width",
    "image_height",
    "grid_rows",
    "grid_cols",
    "r1c1_x",
    "r1c1_y",
    "r1clast_x",
    "r1clast_y",
    "r5c1_x",
    "r5c1_y",
    "r5clast_x",
    "r5clast_y",
)


def _point(x: Any, y: Any, name: str) -> dict[str, float]:
    try:
        point = {"x": float(x), "y": float(y)}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} coordinates must be numeric.") from exc
    if not all(math.isfinite(value) for value in point.values()):
        raise ValueError(f"{name} coordinates must be finite.")
    return point


def _interpolate(
    a: dict[str, float], b: dict[str, float], fraction: float
) -> dict[str, float]:
    return {
        "x": a["x"] + fraction * (b["x"] - a["x"]),
        "y": a["y"] + fraction * (b["y"] - a["y"]),
    }


def build_grid_coordinate_asset(
    *,
    image_ref: str,
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int,
    reference_points: dict[str, Any],
    experiment: str = "",
    set_name: str = "",
    type_name: str = "",
    image_uid: str | None = None,
    run_label: str = "",
    accepted_at: str | None = None,
) -> dict[str, Any]:
    image_ref = image_ref.strip().replace("\\", "/")
    if not image_ref:
        raise ValueError("image_ref is required.")
    for value, label in (
        (image_width, "image_width"),
        (image_height, "image_height"),
        (grid_rows, "grid_rows"),
    ):
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{label} must be a positive integer.")
    if not isinstance(grid_cols, int) or grid_cols < 2:
        raise ValueError("grid_cols must be an integer >= 2.")
    missing = [name for name in REFERENCE_NAMES if name not in reference_points]
    if missing:
        raise ValueError("Missing reference point(s): " + ", ".join(missing))
    refs = {
        name: _point(reference_points[name]["x"], reference_points[name]["y"], name)
        for name in REFERENCE_NAMES
    }

    spots: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for row in range(1, grid_rows + 1):
        vertical_fraction = (row - 1) / 4.0
        left = _interpolate(refs["r1c1"], refs["r5c1"], vertical_fraction)
        right = _interpolate(refs["r1clast"], refs["r5clast"], vertical_fraction)
        rows.append({"row": row, "left": left, "right": right})
        for column in range(1, grid_cols + 1):
            horizontal_fraction = (column - 1) / (grid_cols - 1)
            center = _interpolate(left, right, horizontal_fraction)
            spot_id = f"r{row}c{column}"
            spots[spot_id] = {"row": row, "column": column, **center}

    columns = [
        {
            "column": column,
            "top": {"x": spots[f"r1c{column}"]["x"], "y": spots[f"r1c{column}"]["y"]},
            "bottom": {
                "x": spots[f"r{grid_rows}c{column}"]["x"],
                "y": spots[f"r{grid_rows}c{column}"]["y"],
            },
        }
        for column in range(1, grid_cols + 1)
    ]
    horizontal = {
        "x": (
            (refs["r1clast"]["x"] - refs["r1c1"]["x"])
            + (refs["r5clast"]["x"] - refs["r5c1"]["x"])
        )
        / (2 * (grid_cols - 1)),
        "y": (
            (refs["r1clast"]["y"] - refs["r1c1"]["y"])
            + (refs["r5clast"]["y"] - refs["r5c1"]["y"])
        )
        / (2 * (grid_cols - 1)),
    }
    vertical = {
        "x": (
            (refs["r5c1"]["x"] - refs["r1c1"]["x"])
            + (refs["r5clast"]["x"] - refs["r1clast"]["x"])
        )
        / 8.0,
        "y": (
            (refs["r5c1"]["y"] - refs["r1c1"]["y"])
            + (refs["r5clast"]["y"] - refs["r1clast"]["y"])
        )
        / 8.0,
    }
    timestamp = accepted_at or datetime.now(timezone.utc).isoformat()
    identity_digest = hashlib.sha256(image_ref.casefold().encode("utf-8")).hexdigest()[
        :12
    ]
    asset = {
        "contract_version": CONTRACT_VERSION,
        "asset_type": "GridCoordinateAsset",
        "asset_id": f"grid-{identity_digest}-{METHOD}",
        "status": "accepted",
        "image_ref": image_ref,
        "image_uid": image_uid,
        "metadata": {"experiment": experiment, "set": set_name, "type": type_name},
        "coordinate_space": {
            "id": COORDINATE_SPACE,
            "origin": "top_left",
            "x_axis": "right",
            "y_axis": "down",
            "units": "pixels",
            "position_semantics": "continuous_pixel_centres",
            "image_width": image_width,
            "image_height": image_height,
        },
        "grid": {"rows": grid_rows, "columns": grid_cols},
        "reference_points": refs,
        "basis_vectors": {
            "horizontal_per_column": horizontal,
            "vertical_per_row": vertical,
        },
        "row_coordinates": rows,
        "column_coordinates": columns,
        "spots": spots,
        "transform": {
            "model": "bilinear_row_interpolation_with_reference_row_extrapolation",
            "reference_rows": [1, 5],
            "reference_columns": [1, grid_cols],
        },
        "provenance": {
            "method": METHOD,
            "accepted_at": timestamp,
            "accepted_after": "accepted_alignment_and_crop_export",
            "run_label": run_label,
        },
    }
    validate_grid_coordinate_asset(asset)
    return asset


def validate_grid_coordinate_asset(asset: dict[str, Any]) -> None:
    if (
        asset.get("contract_version") != CONTRACT_VERSION
        or asset.get("asset_type") != "GridCoordinateAsset"
    ):
        raise ValueError("Unsupported GridCoordinateAsset contract.")
    if asset.get("status") != "accepted":
        raise ValueError("Only accepted grid assets are reusable.")
    space = asset.get("coordinate_space", {})
    if space.get("id") != COORDINATE_SPACE or space.get("origin") != "top_left":
        raise ValueError(
            "Grid coordinate space must be explicit source-image top-left pixels."
        )
    grid = asset.get("grid", {})
    rows, columns = grid.get("rows"), grid.get("columns")
    if (
        not isinstance(rows, int)
        or rows < 1
        or not isinstance(columns, int)
        or columns < 2
    ):
        raise ValueError("Invalid grid dimensions.")
    expected_ids = {
        f"r{row}c{column}"
        for row in range(1, rows + 1)
        for column in range(1, columns + 1)
    }
    spots = asset.get("spots", {})
    if set(spots) != expected_ids:
        raise ValueError("Grid spot IDs must cover every rNcN coordinate exactly once.")
    for spot_id, spot in spots.items():
        if not all(math.isfinite(float(spot[key])) for key in ("x", "y")):
            raise ValueError(f"Spot {spot_id} has non-finite coordinates.")
    if (
        len(asset.get("row_coordinates", [])) != rows
        or len(asset.get("column_coordinates", [])) != columns
    ):
        raise ValueError(
            "Row/column coordinate summaries do not match grid dimensions."
        )


def spot_mapping(asset: dict[str, Any]) -> dict[tuple[int, int], tuple[float, float]]:
    validate_grid_coordinate_asset(asset)
    return {
        (spot["row"], spot["column"]): (float(spot["x"]), float(spot["y"]))
        for spot in asset["spots"].values()
    }


def spot_list(asset: dict[str, Any]) -> list[tuple[float, float]]:
    mapping = spot_mapping(asset)
    rows, columns = asset["grid"]["rows"], asset["grid"]["columns"]
    return [
        mapping[(row, column)]
        for row in range(1, rows + 1)
        for column in range(1, columns + 1)
    ]


def _safe_asset_name(image_ref: str) -> str:
    stem = Path(image_ref).stem.casefold()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or "image"
    digest = hashlib.sha256(image_ref.casefold().encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{digest}.grid.json"


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def save_grid_coordinate_asset(
    asset: dict[str, Any], asset_directory: str | Path
) -> Path:
    validate_grid_coordinate_asset(asset)
    directory = Path(asset_directory)
    output = directory / _safe_asset_name(asset["image_ref"])
    _write_json_atomic(output, asset)
    index_path = directory / "index.json"
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read grid asset index: {exc}") from exc
    else:
        index = {"contract_version": CONTRACT_VERSION, "assets": {}}
    if index.get("contract_version") != CONTRACT_VERSION or not isinstance(
        index.get("assets"), dict
    ):
        raise ValueError("Unsupported grid asset index.")
    index["assets"][asset["image_ref"].casefold()] = {
        "asset_id": asset["asset_id"],
        "path": output.name,
        "accepted_at": asset["provenance"]["accepted_at"],
    }
    _write_json_atomic(index_path, index)
    return output


def prepare_grid_handoff(handoff_path: str | Path) -> Path:
    """Create a fresh runtime handoff with the authoritative TSV header."""
    handoff = Path(handoff_path)
    handoff.parent.mkdir(parents=True, exist_ok=True)
    with handoff.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=HANDOFF_FIELDS, delimiter="\t").writeheader()
    return handoff


def grid_handoff_has_complete_row(handoff_path: str | Path) -> bool:
    handoff = Path(handoff_path)
    if not handoff.is_file():
        return False
    with handoff.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if all(row.get(field) is not None for field in HANDOFF_FIELDS):
                return True
    return False


def persist_grid_handoff(
    handoff_path: str | Path, asset_directory: str | Path
) -> list[Path]:
    handoff = Path(handoff_path)
    if not handoff.is_file():
        return []
    with handoff.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        return []
    latest: dict[str, dict[str, str]] = {}
    for row in rows:
        image_ref = (
            f"{row.get('folder', '').strip()}/{row.get('filename', '').strip()}".strip(
                "/"
            )
        )
        if not image_ref:
            raise ValueError("Grid handoff row has no image identity.")
        latest[image_ref] = row
    outputs = []
    for image_ref, row in latest.items():
        refs = {
            name: {"x": row[f"{name}_x"], "y": row[f"{name}_y"]}
            for name in REFERENCE_NAMES
        }
        asset = build_grid_coordinate_asset(
            image_ref=image_ref,
            image_width=positive_int(row.get("image_width"), "image_width"),
            image_height=positive_int(row.get("image_height"), "image_height"),
            grid_rows=positive_int(row.get("grid_rows"), "grid_rows"),
            grid_cols=positive_int(row.get("grid_cols"), "grid_cols"),
            reference_points=refs,
            experiment=row.get("experiment", ""),
            set_name=row.get("set", ""),
            type_name=row.get("type", ""),
            image_uid=clean_optional(row.get("image_uid")),
            run_label=row.get("run_label", ""),
        )
        outputs.append(save_grid_coordinate_asset(asset, asset_directory))
    handoff.unlink()
    return outputs


def positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
    if number < 1:
        raise ValueError(f"{field} must be positive.")
    return number


def clean_optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
