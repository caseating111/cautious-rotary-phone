from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from tools.applets.annotation import compose_matrix
from tools.applets.mixed_tier_matrix import enumerate_crop_candidates

CONTRACT_VERSION = 1
OUTPUTS = {
    "per-experiment",
    "all-strains",
    "all-strains-dedup",
    "label-individual",
}


def _identity(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe(value: Any, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._+-]+", "-", str(value or "").strip())
    return token.strip(" .-") or fallback


def _control_name(value: str) -> str | None:
    compare = " ".join(value.strip().upper().replace("-", " ").replace("_", " ").split())
    if compare == "WT":
        return compare
    if compare.startswith("WT") and len(compare) > 2:
        suffix = compare[2:]
        if suffix[0].isspace() or suffix[0].isdigit():
            return compare
    return None


def _candidate_items(
    state: dict[str, Any], candidate_ids: list[str] | None, source_tier: str
) -> list[dict[str, Any]]:
    candidates = enumerate_crop_candidates(state)
    wanted = list(candidates) if candidate_ids is None else candidate_ids
    if not wanted:
        raise ValueError("Select at least one current crop candidate.")
    unknown = [candidate_id for candidate_id in wanted if candidate_id not in candidates]
    if unknown:
        raise ValueError(f"Unknown or stale crop candidate(s): {unknown}")
    items = [candidates[candidate_id] for candidate_id in wanted]
    items = [item for item in items if item["source_tier"] == source_tier]
    if not items:
        raise ValueError(f"No selected current crops use source tier {source_tier}.")
    return items


def _matrix_spec(alias: str, name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[str] = []
    columns: list[str] = []
    cells: list[dict[str, Any]] = []
    occupied: set[tuple[str, str]] = set()
    for item in items:
        context = item["context"]
        row = str(item["matrix_row"])
        column = str(item["default_column"])
        if row not in rows:
            rows.append(row)
        if column not in columns:
            columns.append(column)
        cell = (row.casefold(), column.casefold())
        if cell in occupied:
            raise ValueError(f"Duplicate native matrix cell: {row} / {column}")
        occupied.add(cell)
        cells.append(
            {
                "image": item["path"],
                "row": row,
                "col": column,
                "strain": row,
                "condition": column,
                "tier": item["state"],
                "candidate_id": item["candidate_id"],
                "image_uid": item["image_uid"],
                "crop_id": item["crop_id"],
                "sha256": item["sha256"],
                "exp": context.get("exp", ""),
            }
        )
    return {
        "alias": alias,
        "name": name,
        "rows": rows,
        "columns": columns,
        "items": cells,
    }


def plan_native_matrix_outputs(
    state: dict[str, Any],
    *,
    candidate_ids: list[str] | None = None,
    source_tier: str = "Unprocessed",
    outputs: list[str] | tuple[str, ...] = tuple(sorted(OUTPUTS)),
    tile_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    if source_tier not in {"Unprocessed", "Processed"}:
        raise ValueError("Native matrix source tier must be Unprocessed or Processed.")
    aliases = list(dict.fromkeys(str(value) for value in outputs))
    if not aliases or any(value not in OUTPUTS for value in aliases):
        raise ValueError("Choose one or more supported native matrix output families.")
    if tile_size is not None and (
        len(tile_size) != 2 or any(not isinstance(value, int) or value < 1 for value in tile_size)
    ):
        raise ValueError("Native matrix tile size must contain two positive integers.")
    selected = _candidate_items(state, candidate_ids, source_tier)
    prepared = []
    for item in selected:
        context = item["context"]
        prepared.append(
            {
                **item,
                "matrix_row": f"{item['strain']} [c{item['column']}]",
                "experiment_row": (
                    f"{context.get('exp') or 'Experiment'} / "
                    f"{item['strain']} [c{item['column']}]"
                ),
            }
        )

    specs: list[dict[str, Any]] = []
    if "per-experiment" in aliases:
        keys = list(
            dict.fromkeys(
                (item["context"].get("exp", ""), item["state"])
                for item in prepared
            )
        )
        for experiment, state_name in keys:
            group = [
                item
                for item in prepared
                if item["context"].get("exp", "") == experiment
                and item["state"] == state_name
            ]
            specs.append(
                _matrix_spec(
                    "per-experiment",
                    f"{_safe(experiment, 'Experiment')}_{state_name}",
                    group,
                )
            )
    for alias in ("all-strains", "all-strains-dedup"):
        if alias not in aliases:
            continue
        for state_name in dict.fromkeys(item["state"] for item in prepared):
            group = [item for item in prepared if item["state"] == state_name]
            for item in group:
                item["matrix_row"] = item["experiment_row"]
            if alias == "all-strains-dedup":
                retained: list[dict[str, Any]] = []
                seen_controls: set[tuple[str, int]] = set()
                for item in group:
                    control = _control_name(item["strain"])
                    key = (control or "", int(item["column"]))
                    if control and key in seen_controls:
                        continue
                    if control:
                        seen_controls.add(key)
                        item = {**item, "matrix_row": f"{control} [c{item['column']}]"}
                    retained.append(item)
                group = retained
            specs.append(_matrix_spec(alias, state_name, group))

    request = {
        "source_tier": source_tier,
        "outputs": aliases,
        "tile_size": list(tile_size) if tile_size else None,
        "candidates": [
            {
                key: item[key]
                for key in (
                    "candidate_id",
                    "image_uid",
                    "crop_id",
                    "source_tier",
                    "state",
                    "sha256",
                )
            }
            for item in prepared
        ],
    }
    root = Path(state["project_root"]).resolve() / "6. Matrices" / "V10 Native"
    return {
        "contract_version": CONTRACT_VERSION,
        "asset_type": "V10NativeMatrixPlan",
        "status": "PROPOSED",
        "preview_only": True,
        "request_id": _identity(request),
        "output_root": str(root),
        "source_tier": source_tier,
        "outputs": aliases,
        "tile_size": list(tile_size) if tile_size else None,
        "specs": specs,
        "items": request["candidates"],
        "labelled_items": prepared if "label-individual" in aliases else [],
    }


def preview_native_matrix_outputs(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("status") != "PROPOSED" or not plan.get("preview_only"):
        raise ValueError("Native matrix preview requires a proposed plan.")
    preview = None
    if plan["specs"]:
        spec = plan["specs"][0]
        tile = tuple(plan["tile_size"]) if plan.get("tile_size") else None
        if tile is None:
            from PIL import Image

            with Image.open(spec["items"][0]["image"]) as image:
                tile = image.size
        preview = compose_matrix(
            spec["items"],
            {"rows": spec["rows"], "cols": spec["columns"], "tile_size": tile, "padding": 10},
        )["preview_image"]
    return {
        "matrix_count": len(plan["specs"]),
        "labelled_crop_count": len(plan["labelled_items"]),
        "preview_image": preview,
    }


def _existing_result(run: Path, request_id: str) -> dict[str, Any] | None:
    manifest = run / "native_matrix_export.json"
    if not manifest.is_file():
        return None
    try:
        result = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return result if result.get("status") == "ACCEPTED" and result.get("request_id") == request_id else None


def publish_native_matrix_outputs(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("status") != "PROPOSED" or not plan.get("preview_only"):
        raise ValueError("Native matrix publishing requires a proposed plan.")
    root = Path(plan["output_root"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_number = 1
    for run in sorted(root.glob("Run *")):
        if not run.is_dir():
            continue
        existing = _existing_result(run, plan["request_id"])
        if existing is not None:
            return existing
        match = re.fullmatch(r"Run (\d+)", run.name)
        if match:
            run_number = max(run_number, int(match.group(1)) + 1)
    output = root / f"Run {run_number:03d}"
    staging = Path(tempfile.mkdtemp(prefix=".v10-native-", dir=root))
    published: list[str] = []
    try:
        for spec in plan["specs"]:
            folder = staging / {
                "per-experiment": "Per Experiment",
                "all-strains": "All Strains",
                "all-strains-dedup": "All Strains Deduplicated WT",
            }[spec["alias"]]
            destination = folder / f"{_safe(spec['name'], 'Matrix')}.png"
            tile = tuple(plan["tile_size"]) if plan.get("tile_size") else None
            if tile is None:
                from PIL import Image

                with Image.open(spec["items"][0]["image"]) as image:
                    tile = image.size
            compose_matrix(
                spec["items"],
                {"rows": spec["rows"], "cols": spec["columns"], "tile_size": tile, "padding": 10},
                str(destination),
            )
            published.append(destination.relative_to(staging).as_posix())
        for item in plan["labelled_items"]:
            context = item["context"]
            destination = (
                staging
                / "Labelled Individual"
                / _safe(context.get("exp"), "Experiment")
                / _safe(item["strain"], "Strain")
                / Path(item["path"]).name
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item["path"], destination)
            published.append(destination.relative_to(staging).as_posix())
        result = {
            "contract_version": CONTRACT_VERSION,
            "asset_type": "V10NativeMatrixResult",
            "status": "ACCEPTED",
            "request_id": plan["request_id"],
            "source_tier": plan["source_tier"],
            "outputs": plan["outputs"],
            "output_directory": str(output),
            "published_paths": published,
            "items": plan["items"],
        }
        (staging / "native_matrix_export.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, output)
        return result
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
