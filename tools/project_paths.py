from __future__ import annotations

import os
from pathlib import Path
from typing import Any

STATE_NAME = "workflow_project.json"

CANONICAL_PARTS: dict[str, tuple[str, ...]] = {
    "raw": ("1. a. Raw",),
    "working": ("1. b. Working",),
    "working_complete": ("2. Cropped", "1. b. Working"),
    "orientation": ("2. Cropped", "Orientation"),
    "cropped": ("2. Cropped",),
    "processed": ("3. Processed",),
    "annotated": ("4. Annotated",),
    "individual_crops": ("5. Individual Crops",),
    "crops_unprocessed": ("5. Individual Crops", "Unprocessed"),
    "crops_processed": ("5. Individual Crops", "Processed"),
    "matrices": ("6. Matrices",),
    "metadata": ("z. Metadata",),
    "state": ("z. Metadata", "State"),
    "grid_coordinates": ("z. Metadata", "State", "GridCoordinates"),
}

LEGACY_PARTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "raw": (("Raw",),),
    "working": (("Working",),),
    "working_complete": (("Processed", "Cropped", "Working"),),
    "orientation": (("Processed", "Oriented"),),
    "cropped": (("Processed", "Cropped"), ("Cropped",)),
    "processed": (("Processed", "Visibility"), ("Processed",)),
    "annotated": (("Annotated",),),
    "individual_crops": (("Crops",), ("Individual Crops",)),
    "crops_unprocessed": (("Crops", "Unprocessed"),),
    "crops_processed": (("Crops", "Processed"),),
    "matrices": (("Matrices",),),
    "metadata": (("Metadata",),),
    "state": (("State",), ("Metadata", "State")),
    "grid_coordinates": (
        ("State", "GridCoordinates"),
        ("Metadata", "GridCoordinates"),
        ("z. Metadata", "GridCoordinates"),
        ("GridCoordinates",),
    ),
}


def canonical_path(project_root: str | Path, key: str) -> Path:
    try:
        parts = CANONICAL_PARTS[key]
    except KeyError as exc:
        raise ValueError(f"Unknown project path key: {key}") from exc
    return Path(project_root).resolve().joinpath(*parts)


def _casefold_child(parent: Path, name: str) -> Path | None:
    if not parent.is_dir():
        return None
    wanted = name.casefold()
    matches = [child for child in parent.iterdir() if child.name.casefold() == wanted]
    if len(matches) > 1:
        raise ValueError(
            f"More than one Windows-equivalent project folder matches {name!r}: "
            + ", ".join(item.name for item in matches)
        )
    return matches[0] if matches else None


def find_casefold_path(project_root: str | Path, parts: tuple[str, ...]) -> Path | None:
    current = Path(project_root).resolve()
    for part in parts:
        child = _casefold_child(current, part)
        if child is None:
            return None
        current = child
    return current


def existing_paths(project_root: str | Path, key: str) -> list[Path]:
    if key not in CANONICAL_PARTS:
        raise ValueError(f"Unknown project path key: {key}")
    candidates = (CANONICAL_PARTS[key], *LEGACY_PARTS.get(key, ()))
    found: list[Path] = []
    seen: set[str] = set()
    for parts in candidates:
        value = find_casefold_path(project_root, parts)
        if value is None:
            continue
        identity = str(value.resolve()).casefold()
        if identity not in seen:
            seen.add(identity)
            found.append(value.resolve())
    return found


def resolve_project_path(
    project_root: str | Path,
    key: str,
    *,
    prefer_existing: bool = True,
) -> Path:
    if prefer_existing:
        found = existing_paths(project_root, key)
        if found:
            return found[0]
    return canonical_path(project_root, key)


def project_uses_legacy_layout(project_root: str | Path) -> bool:
    root = Path(project_root).resolve()
    canonical_markers = ("raw", "working", "metadata", "cropped")
    if any(find_casefold_path(root, CANONICAL_PARTS[key]) for key in canonical_markers):
        return False
    for key in canonical_markers:
        if any(find_casefold_path(root, parts) for parts in LEGACY_PARTS.get(key, ())):
            return True
    return False


def preferred_project_path(project_root: str | Path, key: str) -> Path:
    found = existing_paths(project_root, key)
    if found:
        return found[0]
    if project_uses_legacy_layout(project_root):
        choices = LEGACY_PARTS.get(key, ())
        if choices:
            return Path(project_root).resolve().joinpath(*choices[0])
    return canonical_path(project_root, key)


def working_path(project_root: str | Path) -> Path:
    completed = existing_paths(project_root, "working_complete")
    if completed:
        return completed[0]
    current = existing_paths(project_root, "working")
    return current[0] if current else canonical_path(project_root, "working")


def state_candidates(project_root: str | Path) -> list[Path]:
    root = Path(project_root).resolve()
    folders = existing_paths(root, "state")
    candidates = [folder / STATE_NAME for folder in folders]
    canonical = canonical_path(root, "state") / STATE_NAME
    legacy = root / "State" / STATE_NAME
    for path in (canonical, legacy):
        if str(path).casefold() not in {str(item).casefold() for item in candidates}:
            candidates.append(path)
    return candidates


def locate_state(project_root: str | Path) -> Path:
    matches = [path.resolve() for path in state_candidates(project_root) if path.is_file()]
    identities = {str(path).casefold() for path in matches}
    if len(identities) > 1:
        raise ValueError(
            "More than one project state file exists; remove the ambiguity before continuing:\n- "
            + "\n- ".join(str(path) for path in matches)
        )
    if not matches:
        raise ValueError(f"Project state not found under: {Path(project_root).resolve()}")
    return matches[0]


def project_root_from_state_file(state_file: str | Path) -> Path:
    path = Path(state_file).resolve()
    if path.name.casefold() != STATE_NAME.casefold():
        raise ValueError(f"Not a workflow project state file: {path}")
    state_dir = path.parent
    if state_dir.name.casefold() != "state":
        raise ValueError(f"Project state must be inside a State folder: {path}")
    parent = state_dir.parent
    if parent.name.casefold() in {"z. metadata", "metadata"}:
        return parent.parent.resolve()
    return parent.resolve()


def relative_project_path(path: str | Path, project_root: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(project_root).resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside the project: {path}") from exc


def resolve_recorded_path(value: str | Path, project_root: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path(project_root) / path).resolve()


def rebase_state_paths(
    value: Any,
    old_root: str | Path,
    new_root: str | Path,
) -> Any:
    """Rebase absolute paths below an old project root; preserve external paths."""
    old = Path(old_root).resolve()
    new = Path(new_root).resolve()
    if isinstance(value, dict):
        return {key: rebase_state_paths(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [rebase_state_paths(item, old, new) for item in value]
    if not isinstance(value, str) or not value:
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        relative = path.resolve().relative_to(old)
    except (OSError, ValueError):
        return value
    return str((new / relative).resolve())


def managed_top_level_names() -> set[str]:
    names = {parts[0].casefold() for parts in CANONICAL_PARTS.values()}
    for choices in LEGACY_PARTS.values():
        names.update(parts[0].casefold() for parts in choices)
    return names


def is_managed_descendant(path: str | Path, project_root: str | Path) -> bool:
    candidate = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0].casefold() in managed_top_level_names()


def same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )
