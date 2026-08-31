from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from collections.abc import Collection
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from tools.grid_coordinates import validate_grid_coordinate_asset
from tools.project_dates import (
    folder_name_with_date_style,
    normalize_v10_date,
    unique_folder_date,
)
from tools.project_paths import (
    canonical_path,
    existing_paths,
    managed_top_level_names,
    preferred_project_path,
    rebase_state_paths,
    relative_project_path,
    resolve_recorded_path,
    same_path,
    state_candidates,
    working_path,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
_EXP_TOKEN = re.compile(r"(?<![A-Z0-9])(?:EXP|E)\s*0*(\d+)(?!\d)", re.IGNORECASE)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def loose_image_files(folder: str | Path) -> list[Path]:
    root = Path(folder).resolve()
    if not root.is_dir():
        return []
    return sorted(
        (
            path.resolve()
            for path in root.iterdir()
            if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS
        ),
        key=lambda item: item.name.casefold(),
    )


@dataclass(frozen=True)
class SessionFolderMatch:
    folder: str
    status: Literal["MATCHED", "AMBIGUOUS", "NO_DATE", "NO_MATCH"]
    session_uid: str | None
    candidates: tuple[str, ...]
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _folder_exp(name: str) -> str | None:
    match = _EXP_TOKEN.search(name)
    return str(int(match.group(1))) if match else None


def match_experiment_folder(
    folder: str | Path,
    project_model: dict[str, Any],
    *,
    image_names: Collection[str] | None = None,
    saved_override: str | None = None,
) -> SessionFolderMatch:
    path = Path(folder).resolve()
    sessions = list(project_model.get("sessions", []))
    by_uid = {str(item.get("session_uid") or ""): item for item in sessions}
    if saved_override:
        if saved_override not in by_uid:
            raise ValueError(f"Saved session override is no longer present: {saved_override}")
        return SessionFolderMatch(
            str(path), "MATCHED", saved_override, (saved_override,), ("saved override",)
        )

    folder_date = unique_folder_date(path.name)
    if folder_date is None:
        return SessionFolderMatch(str(path), "NO_DATE", None, (), ())
    candidates: list[dict[str, Any]] = []
    for session in sessions:
        try:
            if normalize_v10_date(session.get("date")) == folder_date:
                candidates.append(session)
        except ValueError:
            continue
    if not candidates:
        return SessionFolderMatch(
            str(path), "NO_MATCH", None, (), (f"folder date={folder_date.isoformat()}",)
        )

    evidence = [f"Date*={folder_date.isoformat()}"]
    exp = _folder_exp(path.name)
    if exp:
        exp_matches = [item for item in candidates if str(item.get("exp") or "") == exp]
        if exp_matches:
            candidates = exp_matches
            evidence.append(f"Exp={exp}")

    supplied_names = {
        str(name).casefold() for name in (image_names or [item.name for item in loose_image_files(path)])
    }
    if len(candidates) > 1 and supplied_names:
        expected_by_session: dict[str, set[str]] = {}
        for image in project_model.get("images", []):
            uid = str(image.get("session_uid") or "")
            original = Path(str(image.get("original") or "")).name.casefold()
            if original:
                expected_by_session.setdefault(uid, set()).add(original)
        overlaps = {
            str(item.get("session_uid") or ""): len(
                supplied_names & expected_by_session.get(str(item.get("session_uid") or ""), set())
            )
            for item in candidates
        }
        best = max(overlaps.values(), default=0)
        if best:
            narrowed = [
                item
                for item in candidates
                if overlaps[str(item.get("session_uid") or "")] == best
            ]
            if len(narrowed) == 1:
                candidates = narrowed
                evidence.append(f"{best} expected Original filename(s)")

    uids = tuple(str(item.get("session_uid") or "") for item in candidates)
    if len(candidates) == 1:
        return SessionFolderMatch(str(path), "MATCHED", uids[0], uids, tuple(evidence))
    return SessionFolderMatch(str(path), "AMBIGUOUS", None, uids, tuple(evidence))


def subset_project_model(
    project_model: dict[str, Any], session_uid: str
) -> dict[str, Any]:
    sessions = [
        copy.deepcopy(item)
        for item in project_model.get("sessions", [])
        if str(item.get("session_uid") or "") == session_uid
    ]
    if len(sessions) != 1:
        raise ValueError(f"Expected one V10 session for {session_uid!r}.")
    images = [
        copy.deepcopy(item)
        for item in project_model.get("images", [])
        if str(item.get("session_uid") or "") == session_uid
    ]
    if not images:
        raise ValueError(f"V10 session has no images: {session_uid}")
    result = {"contract_version": 1, "sessions": sessions, "images": images}
    layouts = project_model.get("layouts")
    if isinstance(layouts, dict):
        wanted = {
            str(item.get("annotation_set") or "")
            for item in images
            if item.get("annotation_set")
        }
        result["layouts"] = {
            key: copy.deepcopy(value) for key, value in layouts.items() if key in wanted
        }
    return result


def discover_experiment_folders(parent: str | Path) -> list[Path]:
    root = Path(parent).resolve()
    if not root.is_dir():
        raise ValueError(f"Parent folder not found: {root}")
    managed = managed_top_level_names()
    return sorted(
        (
            child.resolve()
            for child in root.iterdir()
            if child.is_dir()
            and child.name.casefold() not in managed
            and (
                loose_image_files(child)
                or any(candidate.is_file() for candidate in state_candidates(child))
            )
        ),
        key=lambda item: item.name.casefold(),
    )


def plan_loose_image_import(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    raw = preferred_project_path(root, "raw")
    items: list[dict[str, Any]] = []
    for source in loose_image_files(root):
        destination = raw / source.name
        if destination.is_file():
            status = "UNCHANGED_CURRENT" if _sha256(source) == _sha256(destination) else "TARGET_COLLISION"
        else:
            status = "WOULD_MOVE"
        items.append(
            {
                "source": str(source),
                "destination": str(destination),
                "source_display": f"{root.name} > {source.name}",
                "destination_display": f"{root.name} > {raw.name} > {source.name}",
                "status": status,
            }
        )
    return {
        "project_root": str(root),
        "raw_root": str(raw),
        "preview_only": True,
        "items": items,
        "blockers": [item for item in items if item["status"] == "TARGET_COLLISION"],
    }


def apply_loose_image_import(plan: dict[str, Any]) -> dict[str, Any]:
    if not plan.get("preview_only"):
        raise ValueError("Loose-image import requires a preview plan.")
    if plan.get("blockers"):
        raise ValueError("Loose-image import has target collisions.")
    root = Path(plan["project_root"]).resolve()
    raw = Path(plan["raw_root"]).resolve()
    if raw.parent != root:
        raise ValueError("Raw import destination must be directly inside the project.")
    raw.mkdir(parents=True, exist_ok=True)
    result = copy.deepcopy(plan)
    result["preview_only"] = False
    for item in result["items"]:
        source, destination = Path(item["source"]), Path(item["destination"])
        if item["status"] == "UNCHANGED_CURRENT":
            continue
        if not source.is_file() or destination.exists():
            raise ValueError("Loose-image import changed after preview; preview again.")
        source.replace(destination)
        item["status"] = "MOVED_TO_RAW"
    result["applied_at"] = _timestamp()
    return result


def rename_project_folder_date(
    state: dict[str, Any],
    *,
    style: Literal["dd.mm.yy", "yyyy.mm.dd"] = "yyyy.mm.dd",
) -> tuple[dict[str, Any], Path]:
    old_root = Path(state["project_root"]).resolve()
    session_dates = {
        normalize_v10_date(item.get("date"))
        for item in state["project_model"].get("sessions", [])
        if item.get("date")
    }
    if len(session_dates) != 1:
        raise ValueError("Project folder date renaming requires exactly one V10 session date.")
    new_name = folder_name_with_date_style(old_root.name, next(iter(session_dates)), style)
    new_root = old_root.with_name(new_name)
    if same_path(old_root, new_root):
        return state, old_root
    if new_root.exists():
        raise FileExistsError(f"Renamed project folder already exists: {new_root}")
    old_root.rename(new_root)
    updated = rebase_state_paths(state, old_root, new_root)
    updated["project_root"] = str(new_root)
    updated.setdefault("folder_history", []).append(
        {
            "from": old_root.name,
            "to": new_root.name,
            "changed_at": _timestamp(),
        }
    )
    return updated, new_root


def mark_working_complete(state: dict[str, Any]) -> dict[str, Any]:
    root = Path(state["project_root"]).resolve()
    source = working_path(root)
    destination = canonical_path(root, "working_complete")
    if same_path(source, destination) and destination.is_dir():
        result = {"status": "UNCHANGED_CURRENT", "path": relative_project_path(destination, root)}
    else:
        if not source.is_dir():
            raise FileNotFoundError(f"Working folder not found: {source}")
        if destination.exists():
            raise FileExistsError(f"Completed Working destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        old_relative = relative_project_path(source, root)
        new_relative = relative_project_path(destination, root)
        for record in state.get("images", {}).values():
            value = record.get("working_path")
            if not value:
                continue
            path = resolve_recorded_path(value, root)
            try:
                relative = path.relative_to(source)
            except ValueError:
                continue
            record["working_path"] = (Path(new_relative) / relative).as_posix()
        result = {
            "status": "COMPLETE",
            "method": "MANUAL",
            "from": old_relative,
            "path": new_relative,
        }
    result["completed_at"] = _timestamp()
    state["working_completion"] = result
    return result


def discover_grid_assets(
    project_root: str | Path,
    image_uids: Collection[str],
) -> dict[str, list[Path]]:
    root = Path(project_root).resolve()
    search_roots = existing_paths(root, "grid_coordinates")
    canonical = canonical_path(root, "grid_coordinates")
    if canonical not in search_roots:
        search_roots.append(canonical)
    wanted = set(image_uids)
    matches: dict[str, list[Path]] = {uid: [] for uid in wanted}
    seen: set[str] = set()
    for folder in search_roots:
        if not folder.is_dir():
            continue
        for path in folder.rglob("*.json"):
            identity = os.path.normcase(str(path.resolve()))
            if identity in seen:
                continue
            seen.add(identity)
            try:
                asset = json.loads(path.read_text(encoding="utf-8"))
                validate_grid_coordinate_asset(asset)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            uid = str(asset.get("image_uid") or "")
            if uid in matches:
                matches[uid].append(path.resolve())
    return matches


def _tree_conflicts(source: Path, destination: Path) -> list[str]:
    conflicts: list[str] = []
    if not destination.exists():
        return conflicts
    if source.is_file() or destination.is_file():
        if not source.is_file() or not destination.is_file() or _sha256(source) != _sha256(destination):
            conflicts.append(source.name)
        return conflicts
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if not target.exists():
            continue
        if item.is_dir() != target.is_dir() or item.is_file() and _sha256(item) != _sha256(target):
            conflicts.append(relative.as_posix())
    return conflicts


def plan_layout_migration(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    specifications = (
        (("Processed", "Cropped", "Working"), "working_complete"),
        (("State", "GridCoordinates"), "grid_coordinates"),
        (("Metadata", "GridCoordinates"), "grid_coordinates"),
        (("GridCoordinates",), "grid_coordinates"),
        (("Processed", "Oriented"), "orientation"),
        (("Processed", "Cropped"), "cropped"),
        (("Processed", "Visibility"), "processed"),
        (("Cropped",), "cropped"),
        (("Raw",), "raw"),
        (("Working",), "working"),
        (("Annotated",), "annotated"),
        (("Crops",), "individual_crops"),
        (("Individual Crops",), "individual_crops"),
        (("Matrices",), "matrices"),
        (("Metadata",), "metadata"),
        (("State",), "state"),
    )
    moves: list[dict[str, Any]] = []
    for parts, key in specifications:
        source = root.joinpath(*parts)
        destination = canonical_path(root, key)
        if not source.exists() or same_path(source, destination):
            continue
        conflicts = _tree_conflicts(source, destination)
        status = "CONFLICT" if conflicts else "WOULD_MERGE" if destination.exists() else "WOULD_MOVE"
        moves.append(
            {
                "source": str(source),
                "destination": str(destination),
                "status": status,
                "conflicts": conflicts,
            }
        )
    return {
        "project_root": str(root),
        "preview_only": True,
        "moves": moves,
        "blockers": [item for item in moves if item["status"] == "CONFLICT"],
    }


def _merge_move(source: Path, destination: Path) -> None:
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        return
    if source.is_file():
        if _sha256(source) != _sha256(destination):
            raise FileExistsError(f"Migration target differs: {destination}")
        source.unlink()
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir(), key=lambda value: (value.is_file(), value.name.casefold())):
        _merge_move(item, destination / item.name)
    source.rmdir()


def _rewrite_prefix(value: Any, mappings: list[tuple[Path, Path]], root: Path) -> Any:
    if isinstance(value, dict):
        return {key: _rewrite_prefix(item, mappings, root) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite_prefix(item, mappings, root) for item in value]
    if not isinstance(value, str) or not value:
        return value
    original = Path(value)
    absolute = original.resolve() if original.is_absolute() else (root / original).resolve()
    for source, destination in mappings:
        try:
            relative = absolute.relative_to(source)
        except ValueError:
            continue
        rewritten = destination / relative
        return str(rewritten) if original.is_absolute() else rewritten.relative_to(root).as_posix()
    return value


def apply_layout_migration(plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if not plan.get("preview_only"):
        raise ValueError("Layout migration requires a preview plan.")
    if plan.get("blockers"):
        raise ValueError("Layout migration has conflicting destinations.")
    root = Path(plan["project_root"]).resolve()
    if root != Path(state["project_root"]).resolve():
        raise ValueError("Layout migration plan belongs to a different project.")
    mappings: list[tuple[Path, Path]] = []
    for item in plan.get("moves", []):
        source = Path(item["source"]).resolve()
        destination = Path(item["destination"]).resolve()
        if not source.exists():
            raise ValueError("Project layout changed after preview; preview again.")
        if _tree_conflicts(source, destination):
            raise ValueError("Project layout developed a conflict after preview.")
        _merge_move(source, destination)
        mappings.append((source, destination))
    rewritten = _rewrite_prefix(state, mappings, root)
    state.clear()
    state.update(rewritten)
    state["state_location"] = relative_project_path(
        canonical_path(root, "state") / "workflow_project.json", root
    )
    state.setdefault("folder_history", []).append(
        {
            "type": "NUMBERED_LAYOUT_MIGRATION",
            "moved": [
                {
                    "from": Path(item["source"]).relative_to(root).as_posix(),
                    "to": Path(item["destination"]).relative_to(root).as_posix(),
                }
                for item in plan.get("moves", [])
            ],
            "changed_at": _timestamp(),
        }
    )
    return {**plan, "preview_only": False, "status": "APPLIED", "applied_at": _timestamp()}
