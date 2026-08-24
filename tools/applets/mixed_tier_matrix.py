from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from tools.applets.annotation import compose_matrix

CONTRACT_VERSION = 1
SOURCE_TIERS = {"Unprocessed", "Processed"}
CULTURE_STATES = {"Top", "Low"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    return (root / path if not path.is_absolute() else path).resolve()


def _identity(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _unique_labels(values: list[str], name: str) -> list[str]:
    cleaned = [str(value).strip() for value in values]
    if not cleaned or any(not value for value in cleaned):
        raise ValueError(f"Matrix {name} must be non-empty labels.")
    if len({value.casefold() for value in cleaned}) != len(cleaned):
        raise ValueError(f"Matrix {name} must be unique ignoring case.")
    return cleaned


def _model_context(state: dict[str, Any], image_uid: str) -> dict[str, str]:
    model = state.get("project_model", {})
    image = next(
        (
            item
            for item in model.get("images", [])
            if str(item.get("image_uid") or "") == image_uid
        ),
        {},
    )
    session_uid = str(image.get("session_uid") or "")
    session = next(
        (
            item
            for item in model.get("sessions", [])
            if str(item.get("session_uid") or "") == session_uid
        ),
        {},
    )
    return {
        "exp": str(image.get("exp") or ""),
        "set": str(image.get("set") or ""),
        "condition": str(image.get("condition") or image.get("media") or ""),
        "date": str(session.get("date") or ""),
    }


def enumerate_crop_candidates(
    state: dict[str, Any],
    image_uids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return verified candidates from accepted, non-stale crop-export records."""
    root = Path(state["project_root"]).resolve()
    images = state.get("images")
    if not isinstance(images, dict):
        raise TypeError("Project state images must be an object.")
    wanted = set(image_uids) if image_uids is not None else None
    if wanted is not None:
        unknown = wanted - set(images)
        if unknown:
            raise ValueError(f"Unknown Image UID(s): {sorted(unknown)}")
    candidates: dict[str, dict[str, Any]] = {}
    for image_uid, image in images.items():
        if wanted is not None and image_uid not in wanted:
            continue
        exports = image.get("crop_exports", {})
        if not isinstance(exports, dict):
            raise TypeError(f"Crop exports for {image_uid} must be an object.")
        context = _model_context(state, image_uid)
        for source_tier, export in exports.items():
            if source_tier not in SOURCE_TIERS:
                raise ValueError(
                    f"Unknown crop source tier for {image_uid}: {source_tier}"
                )
            if not isinstance(export, dict):
                raise TypeError(
                    f"Crop export {image_uid}/{source_tier} must be an object."
                )
            if export.get("status") == "STALE":
                continue
            if export.get("status") != "ACCEPTED":
                continue
            output_value = str(export.get("output_directory") or "")
            export_request_id = str(export.get("request_id") or "")
            if not output_value or not export_request_id:
                raise ValueError(
                    f"Crop export {image_uid}/{source_tier} lacks accepted provenance."
                )
            output_dir = _path(root, output_value)
            if not output_dir.is_dir():
                raise ValueError(
                    f"Missing crop output directory for {image_uid}/{source_tier}."
                )
            crops = export.get("crops")
            if not isinstance(crops, list) or not crops:
                raise ValueError(f"Crop export {image_uid}/{source_tier} has no crops.")
            for crop in crops:
                if not isinstance(crop, dict):
                    raise TypeError("Crop export records must be objects.")
                filename = str(crop.get("filename") or "")
                if not filename or Path(filename).name != filename:
                    raise ValueError("Crop filename must be one safe basename.")
                path = (output_dir / filename).resolve()
                if path.parent != output_dir or not path.is_file():
                    raise ValueError(
                        f"Missing crop output for {image_uid}/{source_tier}: {filename}"
                    )
                expected_hash = str(crop.get("sha256") or "")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
                    raise ValueError("Crop output lacks a valid SHA-256 value.")
                if _hash(path).casefold() != expected_hash.casefold():
                    raise ValueError(
                        f"Crop hash mismatch for {image_uid}/{source_tier}: {filename}"
                    )
                state_name = str(crop.get("state") or "")
                if state_name not in CULTURE_STATES:
                    raise ValueError("Crop culture state must be Top or Low.")
                crop_id = str(crop.get("crop_id") or "")
                strain = str(crop.get("strain_label") or "").strip()
                column = crop.get("column")
                if not crop_id or not strain or not isinstance(column, int):
                    raise ValueError("Crop candidate identity is incomplete.")
                provenance = {
                    "image_uid": image_uid,
                    "source_tier": source_tier,
                    "export_request_id": export_request_id,
                    "crop_id": crop_id,
                    "state": state_name,
                    "column": column,
                    "sha256": expected_hash.casefold(),
                }
                candidate_id = f"crop-{_identity(provenance)[:24]}"
                if candidate_id in candidates:
                    raise ValueError(f"Duplicate crop candidate ID: {candidate_id}")
                column_parts = [
                    context[key]
                    for key in ("exp", "set", "condition", "date")
                    if context[key]
                ]
                column_parts.append(image_uid)
                candidates[candidate_id] = {
                    "candidate_id": candidate_id,
                    **provenance,
                    "strain": strain,
                    "context": context,
                    "default_row": strain,
                    "default_column": " / ".join(column_parts),
                    "path": str(path),
                }
    return candidates


def _validate_inputs(plan: dict[str, Any]) -> None:
    for item in plan["items"]:
        path = Path(item["image"])
        if not path.is_file() or _hash(path) != item["sha256"]:
            raise ValueError(f"Matrix input changed after preview: {path}")


def plan_mixed_tier_matrix(
    state: dict[str, Any],
    selections: list[dict[str, str]],
    *,
    rows: list[str],
    columns: list[str],
    output_root: str | Path | None = None,
    tile_size: tuple[int, int] | None = None,
    padding: int = 10,
) -> dict[str, Any]:
    """Resolve an explicit full matrix into a zero-write, hash-bound plan."""
    row_labels = _unique_labels(rows, "rows")
    column_labels = _unique_labels(columns, "columns")
    if not isinstance(selections, list) or not selections:
        raise ValueError("Matrix selections must be a non-empty list.")
    if len(selections) != len(row_labels) * len(column_labels):
        raise ValueError("Every matrix row/column cell must have one selected crop.")
    candidates = enumerate_crop_candidates(state)
    occupied: set[tuple[str, str]] = set()
    used: dict[str, int] = {}
    items: list[dict[str, Any]] = []
    for selection in selections:
        if not isinstance(selection, dict):
            raise TypeError("Matrix selections must be objects.")
        candidate_id = str(selection.get("candidate_id") or "")
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise ValueError(f"Unknown or stale crop candidate: {candidate_id}")
        row = str(selection.get("row") or "").strip()
        column = str(selection.get("column") or "").strip()
        if row not in row_labels or column not in column_labels:
            raise ValueError(
                f"Selection cell is outside the matrix layout: {row}/{column}"
            )
        cell = (row, column)
        if cell in occupied:
            raise ValueError("Matrix selections must contain unique row/column cells.")
        occupied.add(cell)
        used[candidate_id] = used.get(candidate_id, 0) + 1
        items.append(
            {
                "image": candidate["path"],
                "row": row,
                "col": column,
                "strain": row,
                "condition": column,
                "candidate_id": candidate_id,
                "tier": candidate["state"],
                "source_tier": candidate["source_tier"],
                "state": candidate["state"],
                "sha256": candidate["sha256"],
                "image_uid": candidate["image_uid"],
                "export_request_id": candidate["export_request_id"],
                "crop_id": candidate["crop_id"],
                "strain_label": candidate["strain"],
                "crop_column": candidate["column"],
            }
        )
    expected_cells = {(row, column) for row in row_labels for column in column_labels}
    if occupied != expected_cells:
        raise ValueError("Every matrix row/column cell must have one selected crop.")
    if not isinstance(padding, int) or padding < 0:
        raise ValueError("Matrix padding must be a nonnegative integer.")
    if tile_size is None:
        with Image.open(items[0]["image"]) as image:
            tile = image.size
    else:
        tile = tile_size
    if (
        not isinstance(tile, (tuple, list))
        or len(tile) != 2
        or any(not isinstance(value, int) or value < 1 for value in tile)
    ):
        raise ValueError("Matrix tile_size must contain two positive integers.")
    layout = {
        "rows": row_labels,
        "cols": column_labels,
        "tile_size": [int(tile[0]), int(tile[1])],
        "padding": padding,
    }
    request = {
        "matrix_layout": layout,
        "selections": [
            {
                key: item[key]
                for key in (
                    "candidate_id",
                    "row",
                    "col",
                    "tier",
                    "source_tier",
                    "sha256",
                    "image_uid",
                    "export_request_id",
                    "crop_id",
                )
            }
            for item in items
        ],
    }
    request_id = _identity(request)
    root = Path(
        output_root or (Path(state["project_root"]) / "Matrices" / "Mixed Tier")
    ).resolve()
    return {
        "contract_version": CONTRACT_VERSION,
        "asset_type": "MixedTierMatrixPlan",
        "status": "PROPOSED",
        "preview_only": True,
        "request_id": request_id,
        "output_root": str(root),
        "matrix_layout": layout,
        "items": items,
        "warnings": [
            f"Candidate {candidate_id} is deliberately reused in {count} cells."
            for candidate_id, count in used.items()
            if count > 1
        ],
    }


def preview_mixed_tier_matrix(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("status") != "PROPOSED" or not plan.get("preview_only"):
        raise ValueError("Mixed-tier matrix preview requires a proposed plan.")
    _validate_inputs(plan)
    rendered = compose_matrix(plan["items"], plan["matrix_layout"])
    return {
        **plan,
        "status": "PREVIEW",
        "output_dimensions": rendered["output_dimensions"],
        "tile_count": rendered["tile_count"],
        "preview_image": rendered["preview_image"],
    }


def _existing_result(run: Path, request_id: str) -> dict[str, Any] | None:
    manifest = run / "matrix_export.json"
    if not manifest.is_file():
        return None
    try:
        result = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if result.get("status") != "ACCEPTED" or result.get("request_id") != request_id:
        return None
    output = run / "matrix.png"
    if (
        not output.is_file()
        or _hash(output) != result.get("matrix_sha256")
        or Path(result.get("output_directory", "")).resolve() != run.resolve()
    ):
        return None
    return result


def publish_mixed_tier_matrix(plan: dict[str, Any]) -> dict[str, Any]:
    """Atomically publish a validated plan to an immutable numbered run."""
    if plan.get("status") != "PROPOSED" or not plan.get("preview_only"):
        raise ValueError("Mixed-tier matrix publishing requires a proposed plan.")
    _validate_inputs(plan)
    root = Path(plan["output_root"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_number = 1
    for run in sorted(root.glob("Run *")):
        if not run.is_dir():
            continue
        existing = _existing_result(run, plan["request_id"])
        if existing is not None:
            return existing
        match = re.fullmatch(r"Run (d+)", run.name)
        if match:
            run_number = max(run_number, int(match.group(1)) + 1)
    output = root / f"Run {run_number:03d}"
    if output.exists():
        raise FileExistsError(f"Mixed-tier matrix run already exists: {output}")
    staging = Path(tempfile.mkdtemp(prefix=".mixed-matrix-", dir=root))
    try:
        rendered = compose_matrix(
            plan["items"],
            plan["matrix_layout"],
            str(staging / "matrix.png"),
        )
        final_matrix = output / "matrix.png"
        result = {key: value for key, value in plan.items() if key != "preview_only"}
        result.update(
            {
                "asset_type": "MixedTierMatrixResult",
                "status": "ACCEPTED",
                "preview_only": False,
                "output_directory": str(output),
                "output_path": str(final_matrix),
                "output_dimensions": rendered["output_dimensions"],
                "tile_count": rendered["tile_count"],
                "matrix_sha256": _hash(staging / "matrix.png"),
            }
        )
        (staging / "matrix_export.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output)
        return result
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
