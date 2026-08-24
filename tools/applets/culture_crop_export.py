from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from tools.applets.plate_layout import validate_plate_layout
from tools.grid_coordinates import validate_grid_coordinate_asset

CONTRACT_VERSION = 1
STATE_FACTORS = {"Top": 0.375, "Low": 1.375}


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_token(value: Any, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._+-]+", "-", str(value or "").strip())
    return token.strip(" .-") or fallback


def _imagej_round(value: float) -> int:
    if not math.isfinite(value):
        raise ValueError("Crop geometry must be finite.")
    return math.floor(value + 0.5)


def _band_for_row(layout: dict[str, Any], row: float) -> dict[str, Any]:
    matches = [
        band
        for band in layout["strain_bands"]
        if band["row_start"] <= row <= band["row_end"]
    ]
    if len(matches) != 1:
        raise ValueError(
            f"PlateLayout does not map crop representative row {row} to exactly one strain band."
        )
    return matches[0]


def _centre(
    references: dict[str, dict[str, float]],
    factor: float,
    column: int,
    grid_columns: int,
) -> tuple[float, float]:
    fraction = (column - 1) / (grid_columns - 1)
    left_x = references["r1c1"]["x"] + factor * (
        references["r5c1"]["x"] - references["r1c1"]["x"]
    )
    left_y = references["r1c1"]["y"] + factor * (
        references["r5c1"]["y"] - references["r1c1"]["y"]
    )
    right_x = references["r1clast"]["x"] + factor * (
        references["r5clast"]["x"] - references["r1clast"]["x"]
    )
    right_y = references["r1clast"]["y"] + factor * (
        references["r5clast"]["y"] - references["r1clast"]["y"]
    )
    return (
        left_x + fraction * (right_x - left_x),
        left_y + fraction * (right_y - left_y),
    )


def build_crop_records(
    asset: dict[str, Any],
    layout: dict[str, Any],
    metadata: dict[str, Any],
    *,
    states: tuple[str, ...] = ("Top", "Low"),
    columns: tuple[int, ...] | None = None,
    crop_width: int = 130,
    crop_height: int = 546,
) -> list[dict[str, Any]]:
    """Build exact Fiji-compatible Top/Low crop records without reading pixels."""
    validate_grid_coordinate_asset(asset)
    validate_plate_layout(layout)
    if not states or len(set(states)) != len(states):
        raise ValueError("Crop states must be a non-empty unique sequence.")
    if any(state not in STATE_FACTORS for state in states):
        raise ValueError("Crop states must contain only Top and/or Low.")
    if not isinstance(crop_width, int) or crop_width < 1:
        raise ValueError("crop_width must be a positive integer.")
    if not isinstance(crop_height, int) or crop_height < 1:
        raise ValueError("crop_height must be a positive integer.")
    rows = asset["grid"]["rows"]
    grid_columns = asset["grid"]["columns"]
    if rows != 8:
        raise ValueError("Fiji-compatible Top/Low export requires an 8-row grid.")
    if (layout["grid_rows"], layout["grid_cols"]) != (rows, grid_columns):
        raise ValueError("GridCoordinateAsset dimensions do not match PlateLayout.")
    if columns is not None:
        if not columns or len(set(columns)) != len(columns):
            raise ValueError("Selected columns must be a non-empty unique sequence.")
        if any(
            not isinstance(column, int) or not 1 <= column <= grid_columns
            for column in columns
        ):
            raise ValueError("Selected crop column is outside the registered grid.")

    experiment = _safe_token(metadata.get("exp"), "UnknownExp")
    set_name = _safe_token(metadata.get("set"), "Default")
    type_name = _safe_token(
        metadata.get("type") or metadata.get("media") or metadata.get("condition"),
        "UnknownType",
    )
    references = asset["reference_points"]
    records: list[dict[str, Any]] = []
    for state in states:
        factor = STATE_FACTORS[state]
        representative_row = 1.0 + factor * 4.0
        band = _band_for_row(layout, representative_row)
        labels = {int(label["pos"]): str(label["label"]) for label in band["labels"]}
        wanted = columns if columns is not None else tuple(sorted(labels))
        missing = [column for column in wanted if column not in labels]
        if missing:
            raise ValueError(
                f"State {state} strain band has no label for selected column(s): {missing}"
            )
        for column in wanted:
            centre_x, centre_y = _centre(references, factor, column, grid_columns)
            left = _imagej_round(centre_x - crop_width / 2)
            top = _imagej_round(centre_y - crop_height / 2)
            label = labels[column]
            filename = (
                f"{experiment}_{set_name}_{type_name}_{column:02d}_{state}_"
                f"{_safe_token(label, 'UnknownStrain')}.png"
            )
            records.append(
                {
                    "crop_id": f"{state.lower()}-c{column}",
                    "state": state,
                    "column": column,
                    "strain_label": label,
                    "strain_band_order": band["order"],
                    "representative_row": representative_row,
                    "centre": {"x": centre_x, "y": centre_y},
                    "rectangle": {
                        "left": left,
                        "top": top,
                        "right": left + crop_width,
                        "bottom": top + crop_height,
                        "width": crop_width,
                        "height": crop_height,
                    },
                    "filename": filename,
                }
            )
    return records


def _request_id(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_existing_result(path: Path, request_id: str) -> dict[str, Any] | None:
    manifest = path / "crop_export.json"
    if not manifest.is_file():
        return None
    try:
        result = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if result.get("request_id") != request_id or result.get("status") != "ACCEPTED":
        return None
    for record in result.get("crops", []):
        output = path / record.get("filename", "")
        if not output.is_file() or _sha256(output) != record.get("sha256"):
            return None
    return result


def plan_culture_crop_export(
    source_path: str | Path,
    asset: dict[str, Any],
    layout: dict[str, Any],
    metadata: dict[str, Any],
    output_root: str | Path,
    *,
    tier: str,
    states: tuple[str, ...] = ("Top", "Low"),
    columns: tuple[int, ...] | None = None,
    crop_width: int = 130,
    crop_height: int = 546,
) -> dict[str, Any]:
    """Plan a zero-write export and reuse an exact prior numbered run when possible."""
    if tier not in {"Unprocessed", "Processed"}:
        raise ValueError("tier must be Unprocessed or Processed.")
    source = Path(source_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Culture-crop source not found: {source}")
    with Image.open(source) as image:
        dimensions = image.size
    space = asset.get("coordinate_space", {})
    if (space.get("image_width"), space.get("image_height")) != dimensions:
        raise ValueError("Grid coordinate-space dimensions do not match crop source.")
    records = build_crop_records(
        asset,
        layout,
        metadata,
        states=states,
        columns=columns,
        crop_width=crop_width,
        crop_height=crop_height,
    )
    for record in records:
        box = record["rectangle"]
        if (
            box["left"] < 0
            or box["top"] < 0
            or box["right"] > dimensions[0]
            or box["bottom"] > dimensions[1]
        ):
            raise ValueError(
                "Crop would cross source bounds before any output write: "
                f"column {record['column']} {record['state']}."
            )

    source_hash = _sha256(source)
    image_uid = str(metadata.get("image_uid") or "")
    request = {
        "image_uid": image_uid,
        "source_sha256": source_hash,
        "grid_asset_id": asset["asset_id"],
        "layout_id": layout["layout_id"],
        "tier": tier,
        "states": list(states),
        "columns": list(columns) if columns is not None else None,
        "crop_width": crop_width,
        "crop_height": crop_height,
        "crop_geometry": [
            {
                "crop_id": record["crop_id"],
                "rectangle": record["rectangle"],
                "filename": record["filename"],
            }
            for record in records
        ],
    }
    identity = _request_id(request)
    root = Path(output_root).resolve()
    run_number = 1
    if root.is_dir():
        for run in sorted(root.glob("Run *")):
            if not run.is_dir():
                continue
            existing = _valid_existing_result(run, identity)
            if existing is not None:
                return {
                    "contract_version": CONTRACT_VERSION,
                    "asset_type": "CultureCropExportPlan",
                    "status": "UNCHANGED_CURRENT",
                    "preview_only": True,
                    "request_id": identity,
                    "source_path": str(source),
                    "source_sha256": source_hash,
                    "source_dimensions": list(dimensions),
                    "image_uid": image_uid,
                    "grid_asset_id": asset["asset_id"],
                    "layout_id": layout["layout_id"],
                    "output_directory": str(run),
                    "tier": tier,
                    "crops": records,
                    "existing_result": existing,
                }
            match = re.fullmatch(r"Run (\d+)", run.name)
            if match:
                run_number = max(run_number, int(match.group(1)) + 1)
    output_directory = root / f"Run {run_number:03d}"
    return {
        "contract_version": CONTRACT_VERSION,
        "asset_type": "CultureCropExportPlan",
        "status": "PROPOSED",
        "preview_only": True,
        "request_id": identity,
        "source_path": str(source),
        "source_sha256": source_hash,
        "source_dimensions": list(dimensions),
        "image_uid": image_uid,
        "grid_asset_id": asset["asset_id"],
        "layout_id": layout["layout_id"],
        "tier": tier,
        "output_directory": str(output_directory),
        "crops": records,
    }


def export_culture_crops(plan: dict[str, Any]) -> dict[str, Any]:
    """Write a fully validated plan into a new numbered run using atomic publish."""
    if plan.get("status") == "UNCHANGED_CURRENT":
        return plan["existing_result"]
    if plan.get("status") != "PROPOSED" or not plan.get("preview_only"):
        raise ValueError("Culture crop export requires a current preview plan.")
    source = Path(plan["source_path"])
    if _sha256(source) != plan["source_sha256"]:
        raise ValueError("Culture-crop source changed after preview; preview again.")
    output = Path(plan["output_directory"])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Planned culture-crop run already exists: {output}")
    staging = Path(tempfile.mkdtemp(prefix=".crop-export-", dir=output.parent))
    try:
        result_records: list[dict[str, Any]] = []
        with Image.open(source) as image:
            for record in plan["crops"]:
                box = record["rectangle"]
                crop = image.crop(
                    (box["left"], box["top"], box["right"], box["bottom"])
                )
                crop_path = staging / record["filename"]
                crop.save(crop_path, format="PNG")
                result_records.append({**record, "sha256": _sha256(crop_path)})
        result = {
            "contract_version": CONTRACT_VERSION,
            "asset_type": "CultureCropExportResult",
            "status": "ACCEPTED",
            "preview_only": False,
            "request_id": plan["request_id"],
            "source_path": str(source),
            "source_sha256": plan["source_sha256"],
            "source_dimensions": plan["source_dimensions"],
            "image_uid": plan.get("image_uid", ""),
            "grid_asset_id": plan["grid_asset_id"],
            "layout_id": plan["layout_id"],
            "tier": plan["tier"],
            "output_directory": str(output),
            "crops": result_records,
        }
        (staging / "crop_export.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, output)
        return result
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
