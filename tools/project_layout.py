from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


INVALID_PREFIX_CHARS = set('<>:"/\\|?*;')


@dataclass(frozen=True)
class ProjectLayout:
    project_root: Path
    image_root: Path
    crop_output: Path
    matrix_output: Path
    metadata_dir: Path


def default_prefix(today: date | None = None) -> str:
    return (today or date.today()).strftime("%d.%m.%y")


def validate_prefix(value: str) -> str:
    prefix = value.strip()
    if not prefix:
        raise SystemExit("Project prefix cannot be blank.")
    if prefix in {".", ".."}:
        raise SystemExit("Project prefix cannot be '.' or '..'.")
    invalid = sorted({char for char in prefix if char in INVALID_PREFIX_CHARS or ord(char) < 32})
    if invalid:
        shown = " ".join(repr(char) for char in invalid)
        raise SystemExit(
            "Project prefix contains characters that are unsafe for Windows/Fiji paths: " + shown
        )
    if prefix.endswith((" ", ".")):
        raise SystemExit("Project prefix cannot end with a space or period on Windows.")
    return prefix


def existing_layout_for_raw(image_root: Path) -> ProjectLayout | None:
    image_root = image_root.resolve()
    raw_dir = image_root.parent
    if raw_dir.name.casefold() != "raw":
        return None
    project_root = raw_dir.parent
    if not project_root.name.casefold().endswith(("_" + image_root.name).casefold()):
        return None
    return ProjectLayout(
        project_root=project_root,
        image_root=image_root,
        crop_output=project_root / "Crops",
        matrix_output=project_root / "Matrices",
        metadata_dir=project_root / "Metadata",
    )


def planned_layout(image_root: Path, prefix: str) -> ProjectLayout:
    image_root = image_root.resolve()
    if not image_root.is_dir():
        raise SystemExit(f"Image root not found: {image_root}")

    existing = existing_layout_for_raw(image_root)
    if existing is not None:
        return existing

    prefix = validate_prefix(prefix)
    project_root = image_root.parent / f"{prefix}_{image_root.name}"
    return ProjectLayout(
        project_root=project_root,
        image_root=project_root / "Raw" / image_root.name,
        crop_output=project_root / "Crops",
        matrix_output=project_root / "Matrices",
        metadata_dir=project_root / "Metadata",
    )


def _cleanup_empty_project(layout: ProjectLayout) -> None:
    for path in (layout.metadata_dir, layout.matrix_output, layout.crop_output, layout.image_root.parent):
        try:
            path.rmdir()
        except OSError:
            pass
    try:
        layout.project_root.rmdir()
    except OSError:
        pass


def initialize_project(image_root: Path, prefix: str) -> ProjectLayout:
    source = image_root.resolve()
    if not source.is_dir():
        raise SystemExit(f"Image root not found: {source}")

    existing = existing_layout_for_raw(source)
    if existing is not None:
        for folder in (existing.crop_output, existing.matrix_output, existing.metadata_dir):
            folder.mkdir(parents=True, exist_ok=True)
        return existing

    layout = planned_layout(source, prefix)
    if layout.project_root.exists():
        raise SystemExit(
            f"Project folder already exists; refusing to merge or overwrite it automatically: {layout.project_root}"
        )

    try:
        layout.image_root.parent.mkdir(parents=True, exist_ok=False)
        layout.crop_output.mkdir()
        layout.matrix_output.mkdir()
        layout.metadata_dir.mkdir()
        # The project is deliberately created beside the selected source folder,
        # so this is a same-filesystem directory rename rather than an image copy.
        # Image bytes remain untouched; only the folder path changes.
        source.rename(layout.image_root)
    except OSError as exc:
        _cleanup_empty_project(layout)
        raise SystemExit(f"Could not create project layout: {exc}") from exc

    return layout
