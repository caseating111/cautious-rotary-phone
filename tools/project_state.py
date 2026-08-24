from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
STATE_NAME = "workflow_project.json"
DOWNSTREAM = {
    "orientation": ("crop", "grid", "visibility", "annotation", "crop_exports"),
    "crop": ("grid", "visibility", "annotation", "crop_exports"),
    "grid": ("visibility", "annotation", "crop_exports"),
    "visibility": ("annotation",),
}


def state_path(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / "State" / STATE_NAME


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _image_records(project_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for image in project_model.get("images", []):
        uid = str(image.get("image_uid", "")).strip()
        if not uid or uid in records:
            raise ValueError("ProjectModel image UIDs must be non-empty and unique.")
        records[uid] = {
            "image_uid": uid,
            "session_uid": image.get("session_uid"),
            "layout_id": image.get("annotation_set"),
            "raw_path": None,
            "working_path": None,
        }
    return records


def new_project_state(
    project_root: str | Path,
    project_model: dict[str, Any],
    *,
    v10_workbook: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    state = {
        "contract_version": CONTRACT_VERSION,
        "asset_type": "WorkflowProjectState",
        "project_root": str(root),
        "v10_workbook": str(Path(v10_workbook).resolve()) if v10_workbook else None,
        "project_model": copy.deepcopy(project_model),
        "crop_calibrations": {},
        "matrix_exports": {},
        "images": _image_records(project_model),
        "updated_at": _timestamp(),
    }
    validate_project_state(state)
    return state


def validate_project_state(state: dict[str, Any]) -> None:
    if (
        state.get("contract_version") != CONTRACT_VERSION
        or state.get("asset_type") != "WorkflowProjectState"
    ):
        raise ValueError("Unsupported WorkflowProjectState contract.")
    root = state.get("project_root")
    if not isinstance(root, str) or not root.strip():
        raise ValueError("Project state requires project_root.")
    model = state.get("project_model")
    if not isinstance(model, dict) or model.get("contract_version") != 1:
        raise ValueError("Project state requires ProjectModel v1.")
    images = state.get("images")
    if not isinstance(images, dict):
        raise TypeError("Project state images must be keyed by Image UID.")
    expected = {
        str(image.get("image_uid", "")).strip() for image in model.get("images", [])
    }
    if not expected or set(images) != expected:
        raise ValueError("Project state image keys must match ProjectModel Image UIDs.")
    for uid, record in images.items():
        if not isinstance(record, dict) or record.get("image_uid") != uid:
            raise ValueError(f"Invalid project-state image record: {uid}")
    if not isinstance(state.get("crop_calibrations"), dict):
        raise TypeError("crop_calibrations must be an object.")
    matrix_exports = state.get("matrix_exports", {})
    if not isinstance(matrix_exports, dict):
        raise TypeError("matrix_exports must be an object.")
    for request_id, result in matrix_exports.items():
        if (
            not isinstance(request_id, str)
            or not request_id
            or not isinstance(result, dict)
            or result.get("status") != "ACCEPTED"
            or result.get("request_id") != request_id
        ):
            raise ValueError("Invalid accepted matrix export record.")
    for uid, record in images.items():
        exports = record.get("crop_exports")
        if exports is not None and not isinstance(exports, dict):
            raise TypeError(f"crop_exports for {uid} must be an object.")
        if isinstance(exports, dict):
            for tier, result in exports.items():
                if (
                    not isinstance(tier, str)
                    or not tier.strip()
                    or not isinstance(result, dict)
                ):
                    raise ValueError(f"Invalid crop export record for {uid}.")


def save_project_state(state: dict[str, Any], path: str | Path | None = None) -> Path:
    validate_project_state(state)
    state["updated_at"] = _timestamp()
    destination = Path(path) if path else state_path(state["project_root"])
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, destination)
    return destination


def load_project_state(path_or_root: str | Path) -> dict[str, Any]:
    path = Path(path_or_root).resolve()
    if path.is_dir() or path.suffix.casefold() != ".json":
        path = state_path(path)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Project state not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read project state {path}: {exc}") from exc
    validate_project_state(state)
    return state


def _record(state: dict[str, Any], image_uid: str) -> dict[str, Any]:
    validate_project_state(state)
    try:
        return state["images"][image_uid]
    except KeyError as exc:
        raise ValueError(
            f"Image UID is not present in project state: {image_uid}"
        ) from exc


def _mark_stale(record: dict[str, Any], changed_asset: str) -> None:
    for dependent in DOWNSTREAM.get(changed_asset, ()):
        value = record.get(dependent)
        if dependent == "crop_exports" and isinstance(value, dict):
            for export in value.values():
                if isinstance(export, dict) and export.get("status") != "STALE":
                    export["status"] = "STALE"
                    export["stale_reason"] = f"{changed_asset} changed"
                    export["stale_at"] = _timestamp()
        elif isinstance(value, dict) and value.get("status") != "STALE":
            value["status"] = "STALE"
            value["stale_reason"] = f"{changed_asset} changed"
            value["stale_at"] = _timestamp()

    # Visibility changes affect only crops exported from the processed derivative.
    if changed_asset == "visibility":
        exports = record.get("crop_exports")
        if isinstance(exports, dict):
            for tier, export in exports.items():
                processed = isinstance(export, dict) and (
                    str(tier).casefold() == "processed"
                    or str(export.get("source_kind", "")).casefold() == "processed"
                )
                if (
                    processed
                    and isinstance(export, dict)
                    and export.get("status") != "STALE"
                ):
                    export["status"] = "STALE"
                    export["stale_reason"] = "visibility changed"
                    export["stale_at"] = _timestamp()


def record_setup_result(state: dict[str, Any], result: dict[str, Any]) -> None:
    for image in result.get("images", []):
        record = _record(state, image["image_uid"])
        record["raw_path"] = image.get("raw_path")
        record["working_path"] = image.get("working_path")
        record["setup_disposition"] = image.get("disposition")
    state["setup"] = {
        "status": "APPLIED" if not result.get("preview_only") else "PREVIEW",
        "summary": copy.deepcopy(result.get("summary", {})),
        "conversion_map_path": result.get("conversion_map_path"),
        "updated_at": _timestamp(),
    }


def record_crop_calibration(state: dict[str, Any], calibration: dict[str, Any]) -> None:
    calibration_id = str(calibration.get("calibration_id", "")).strip()
    if not calibration_id:
        raise ValueError("Crop calibration requires calibration_id.")
    state["crop_calibrations"][calibration_id] = copy.deepcopy(calibration)


def record_orientation(
    state: dict[str, Any], image_uid: str, result: dict[str, Any]
) -> None:
    if result.get("status") not in {"ACCEPTED", "SKIPPED"}:
        raise ValueError(
            "Only accepted or skipped orientation results may be recorded."
        )
    record = _record(state, image_uid)
    prior = record.get("orientation")
    record["orientation"] = copy.deepcopy(result)
    if prior != record["orientation"]:
        _mark_stale(record, "orientation")


def record_crop(state: dict[str, Any], image_uid: str, result: dict[str, Any]) -> None:
    if result.get("status") not in {"ACCEPTED", "SKIPPED"}:
        raise ValueError("Only accepted or skipped crop results may be recorded.")
    record = _record(state, image_uid)
    prior = record.get("crop")
    record["crop"] = copy.deepcopy(result)
    if prior != record["crop"]:
        _mark_stale(record, "crop")


def record_grid_asset(
    state: dict[str, Any], image_uid: str, asset: dict[str, Any], asset_path: str | Path
) -> None:
    if (
        asset.get("asset_type") != "GridCoordinateAsset"
        or asset.get("status") != "accepted"
    ):
        raise ValueError("Only accepted GridCoordinateAsset values may be recorded.")
    record = _record(state, image_uid)
    prior = record.get("grid")
    current = {
        "status": "ACCEPTED",
        "asset_id": asset.get("asset_id"),
        "coordinate_space": copy.deepcopy(asset.get("coordinate_space")),
        "path": str(Path(asset_path).resolve()),
    }
    changed = not isinstance(prior, dict) or any(
        prior.get(key) != value for key, value in current.items()
    )
    current["recorded_at"] = _timestamp()
    record["grid"] = current
    if changed:
        _mark_stale(record, "grid")


def record_crop_export(
    state: dict[str, Any],
    image_uid: str,
    tier: str,
    result: dict[str, Any],
) -> None:
    tier_name = str(tier or "").strip()
    if tier_name not in {"Unprocessed", "Processed"}:
        raise ValueError("Crop export tier must be Unprocessed or Processed.")
    if result.get("status") != "ACCEPTED":
        raise ValueError("Only accepted crop exports may be recorded.")
    record = _record(state, image_uid)
    exports = record.setdefault("crop_exports", {})
    if not isinstance(exports, dict):
        raise TypeError("crop_exports must be an object.")
    current = copy.deepcopy(result)
    current["tier"] = tier_name
    prior = exports.get(tier_name)
    same_request = (
        isinstance(prior, dict)
        and prior.get("request_id")
        and prior.get("request_id") == current.get("request_id")
    )
    if same_request:
        current["recorded_at"] = prior.get("recorded_at", _timestamp())
    else:
        current["recorded_at"] = _timestamp()
        if prior is not None:
            current["replaced_at"] = _timestamp()
    exports[tier_name] = current


def record_matrix_export(state: dict[str, Any], result: dict[str, Any]) -> None:
    if result.get("status") != "ACCEPTED":
        raise ValueError("Only accepted matrix exports may be recorded.")
    request_id = str(result.get("request_id") or "")
    if not request_id:
        raise ValueError("Matrix export requires request_id.")
    validate_project_state(state)
    exports = state.setdefault("matrix_exports", {})
    current = copy.deepcopy(result)
    prior = exports.get(request_id)
    if isinstance(prior, dict):
        current["recorded_at"] = prior.get("recorded_at", _timestamp())
    else:
        current["recorded_at"] = _timestamp()
    exports[request_id] = current


def record_derivative(
    state: dict[str, Any],
    image_uid: str,
    kind: str,
    result: dict[str, Any],
) -> None:
    if kind not in {"visibility", "annotation"}:
        raise ValueError(f"Unsupported derivative kind: {kind}")
    if result.get("status") != "ACCEPTED":
        raise ValueError("Only accepted derivative results may be recorded.")
    record = _record(state, image_uid)
    prior = record.get(kind)
    current = copy.deepcopy(result)
    record[kind] = current
    if prior != current:
        _mark_stale(record, kind)
