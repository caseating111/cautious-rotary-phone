from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from tools.grid_coordinates import validate_grid_coordinate_asset

AUTOMATIC_STAGES = {"culture", "visibility", "annotation"}


def normalize_uids(values: list[str] | tuple[str, ...]) -> list[str]:
    result = []
    for value in values:
        uid = str(value).strip()
        if not uid:
            raise ValueError("Batch Image UIDs cannot be blank.")
        if uid in result:
            raise ValueError(f"Duplicate batch Image UID: {uid}")
        result.append(uid)
    if not result:
        raise ValueError("Select at least one Image UID for the batch.")
    return result


def plan_automatic_batch(
    workflow: Any,
    stage: str,
    image_uids: list[str] | tuple[str, ...],
    *,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preflight every selected image without writing any accepted output."""
    if stage not in AUTOMATIC_STAGES:
        raise ValueError(f"Unsupported automatic batch stage: {stage}")
    uids = normalize_uids(image_uids)
    settings = copy.deepcopy(options or {})
    items = []
    for uid in uids:
        if stage == "culture":
            proposal = workflow.preview_culture_crop_export(uid, **settings)
            count = len(proposal["crops"])
        elif stage == "visibility":
            proposal, _preview = workflow.propose_visibility(
                uid, settings.get("preset")
            )
            count = 1
        else:
            request = workflow.default_annotation_request(uid)
            request["labels"].update(settings.get("label_overrides", {}))
            source_kind = settings.get("source_kind")
            if source_kind is None:
                proposal, _preview = workflow.propose_annotation(
                    uid, request, settings.get("preset")
                )
            else:
                proposal, _preview = workflow.propose_annotation(
                    uid,
                    request,
                    settings.get("preset"),
                    source_kind=source_kind,
                )
            proposal.pop("preview_image", None)
            count = 1
        items.append({"image_uid": uid, "proposal": proposal, "output_count": count})
    return {
        "contract_version": 1,
        "asset_type": "AppletBatchPlan",
        "stage": stage,
        "status": "PROPOSED",
        "image_uids": uids,
        "options": settings,
        "items": items,
        "output_count": sum(item["output_count"] for item in items),
    }


def execute_automatic_batch(workflow: Any, plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("asset_type") != "AppletBatchPlan" or plan.get("status") != "PROPOSED":
        raise ValueError("Batch execution requires a proposed AppletBatchPlan.")
    stage = plan.get("stage")
    if stage not in AUTOMATIC_STAGES:
        raise ValueError("Batch plan has an unsupported stage.")
    results = []
    for item in plan["items"]:
        uid, proposal = item["image_uid"], item["proposal"]
        if stage == "culture":
            accepted = workflow.accept_culture_crop_export(uid, proposal)
        elif stage == "visibility":
            accepted = workflow.accept_visibility(uid, proposal)[0]
        else:
            accepted = workflow.accept_annotation(uid, proposal)[0]
        results.append({"image_uid": uid, "result": accepted})
    result = copy.deepcopy(plan)
    result["status"] = "ACCEPTED"
    result["results"] = results
    result.pop("items", None)
    return result


def plan_grid_directory(
    directory: str | Path,
    image_uids: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """Match selected images to validated grid assets without changing project state."""
    uids = normalize_uids(image_uids)
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Grid asset directory not found: {root}")
    matches: dict[str, str] = {}
    for path in sorted(root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate_grid_coordinate_asset(value)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        uid = str(value.get("image_uid") or "").strip()
        if uid in uids:
            if uid in matches:
                raise ValueError(f"Multiple grid assets match Image UID {uid}.")
            matches[uid] = str(path.resolve())
    missing = [uid for uid in uids if uid not in matches]
    if missing:
        raise ValueError("No validated grid asset found for: " + ", ".join(missing))
    return {
        "contract_version": 1,
        "asset_type": "AppletBatchPlan",
        "stage": "grid",
        "status": "PROPOSED",
        "image_uids": uids,
        "items": [{"image_uid": uid, "path": matches[uid]} for uid in uids],
        "output_count": len(uids),
    }


def execute_grid_batch(workflow: Any, plan: dict[str, Any]) -> dict[str, Any]:
    if (
        plan.get("asset_type") != "AppletBatchPlan"
        or plan.get("stage") != "grid"
        or plan.get("status") != "PROPOSED"
    ):
        raise ValueError("Grid batch execution requires a proposed grid plan.")
    results = [
        {
            "image_uid": item["image_uid"],
            "result": workflow.attach_grid_asset(item["image_uid"], item["path"]),
        }
        for item in plan["items"]
    ]
    result = copy.deepcopy(plan)
    result["status"] = "ACCEPTED"
    result["results"] = results
    result.pop("items", None)
    return result
