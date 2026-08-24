from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from .v10_adapter import reconcile_image_files

_INVALID_NAME_CHARS = set('<>:"/\\|?*;')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_PROJECT_DIRECTORIES = {
    "raw": ("Raw",),
    "working": ("Working",),
    "processed": ("Processed",),
    "annotated": ("Annotated",),
    "crops_unprocessed": ("Crops", "Unprocessed"),
    "crops_processed": ("Crops", "Processed"),
    "matrices": ("Matrices",),
    "metadata": ("Metadata",),
    "state": ("State",),
}


def _safe_relative_path(value: str, *, field: str) -> str:
    text = str(value or "").strip()
    if not text or Path(text).is_absolute() or Path(text).drive:
        raise ValueError(f"{field} must be a non-empty relative path.")
    raw_parts = text.replace("\\", "/").split("/")
    if any(not part or part in {".", ".."} for part in raw_parts):
        raise ValueError(f"{field} cannot contain empty or dot path components.")
    for part in raw_parts:
        stem = part.split(".", 1)[0].upper()
        if (
            any(ord(char) < 32 or char in _INVALID_NAME_CHARS for char in part)
            or part.endswith((" ", "."))
            or stem in _RESERVED_WINDOWS_NAMES
        ):
            raise ValueError(f"{field} contains an unsafe Windows filename component.")
    return "/".join(raw_parts)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Source path is outside the project root: {path}") from exc


def _recursive_files(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return [str(path.resolve()) for path in sorted(folder.rglob("*")) if path.is_file()]


def initialize_project_tree(
    project_root: str | Path, create_subdirs: bool = True
) -> dict[str, str]:
    """Return or create additive directories compatible with ProjectLayout."""
    root = Path(project_root).resolve()
    directories = {
        key: str(root.joinpath(*parts)) for key, parts in _PROJECT_DIRECTORIES.items()
    }
    if create_subdirs:
        for directory in directories.values():
            Path(directory).mkdir(parents=True, exist_ok=True)
    return directories


def _files_by_session(
    project_model: dict[str, Any],
    raw_root: Path,
    custom_session_folders: dict[str, str],
) -> dict[str, list[str]]:
    all_files = _recursive_files(raw_root)
    named_folders: dict[str, list[Path]] = {}
    if raw_root.is_dir():
        for path in raw_root.rglob("*"):
            if path.is_dir():
                named_folders.setdefault(path.name.casefold(), []).append(path)
    result: dict[str, list[str]] = {}
    for session in project_model.get("sessions", []):
        uid = str(session.get("session_uid", ""))
        custom = custom_session_folders.get(uid)
        if custom:
            folder = Path(custom).resolve()
            try:
                folder.relative_to(raw_root)
            except ValueError as exc:
                raise ValueError(
                    f"Custom session folder for {uid} must remain inside Raw."
                ) from exc
            result[uid] = _recursive_files(folder)
            continue
        matches = named_folders.get(uid.casefold(), [])
        result[uid] = (
            sorted({file for folder in matches for file in _recursive_files(folder)})
            if matches
            else all_files
        )
    return result


def generate_conversion_map_text(
    project_model: dict[str, Any],
    rename_results: list[dict[str, Any]],
    project_root: str | Path | None = None,
) -> str:
    """Build the human audit map using project-relative paths only."""
    results = {result["image_uid"]: result for result in rename_results}
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for image in project_model.get("images", []):
        grouped.setdefault(str(image.get("exp") or "Unknown"), {}).setdefault(
            str(image.get("set") or "Default"), []
        ).append(image)
    lines = [
        "V10 IMAGE NAME CONVERSION & AUDIT MAP",
        "Canonical identity is Image UID; paths are relative to the project root.",
        "",
    ]
    for experiment in sorted(grouped):
        lines.append(f"=== Experiment {experiment} ===")
        for set_name in sorted(grouped[experiment]):
            lines.append(f"-- Set {set_name} --")
            for image in grouped[experiment][set_name]:
                uid = image["image_uid"]
                result = results.get(uid, {})
                raw_path = result.get("raw_path") or "EXPECTED_NOT_PRESENT"
                working_path = result.get("working_path") or "NOT_PLANNED"
                lines.append(f"{raw_path} -> {working_path}")
                lines.append(
                    f"  UID={uid} Session={image.get('session_uid')} "
                    f"Status={result.get('disposition', 'UNKNOWN')}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_conversion_map(path: Path, text: str) -> None:
    if path.is_file():
        prior = path.read_text(encoding="utf-8")
        if prior == text:
            return
        digest = hashlib.sha256(prior.encode("utf-8")).hexdigest()[:12]
        history = path.parent / "History" / f"image_name_conversions.{digest}.txt"
        if not history.exists():
            _atomic_write_text(history, prior)
    _atomic_write_text(path, text)


def prepare_working_copy(
    project_model: dict[str, Any],
    project_root: str | Path,
    raw_root: str | Path | None = None,
    working_root: str | Path | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preview or apply V10 reconciliation into a non-destructive Working tree."""
    options = options or {}
    enable_rename = bool(options.get("enable_rename", True))
    preview_only = bool(options.get("preview_only", False))
    write_conversion_map = bool(options.get("write_conversion_map", True))
    collision_policy = options.get("collision_policy", "error")
    if collision_policy not in {"error", "disambiguate_with_uid"}:
        raise ValueError(f"Unsupported collision_policy: {collision_policy}")

    root = Path(project_root).resolve()
    raw = Path(raw_root).resolve() if raw_root else root / "Raw"
    working = Path(working_root).resolve() if working_root else root / "Working"
    for path, label in ((raw, "raw_root"), (working, "working_root")):
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"{label} must remain inside the project root.") from exc

    if not preview_only:
        initialize_project_tree(root)
        raw.mkdir(parents=True, exist_ok=True)
        working.mkdir(parents=True, exist_ok=True)

    provenance_map = {
        str(uid): str(Path(path).resolve())
        for uid, path in options.get("provenance_map", {}).items()
    }
    for uid, path in provenance_map.items():
        try:
            Path(path).relative_to(raw)
        except ValueError as exc:
            raise ValueError(
                f"Provenance path for {uid} must remain inside Raw."
            ) from exc

    files_by_session = _files_by_session(
        project_model, raw, options.get("custom_session_folders", {})
    )
    reconciliation = reconcile_image_files(
        project_model,
        files_by_session=files_by_session,
        provenance_map=provenance_map,
    )
    reconciled = {item["image_uid"]: item for item in reconciliation.get("images", [])}
    claimed = Counter(
        str(Path(item["matched_file"]).resolve()).casefold()
        for item in reconciled.values()
        if item.get("status") == "READY" and item.get("matched_file")
    )

    destinations: dict[str, str] = {}
    plans: list[dict[str, Any]] = []
    for image in project_model.get("images", []):
        uid = str(image["image_uid"])
        session_uid = str(image.get("session_uid") or "")
        match = reconciled.get(uid, {})
        source_value = match.get("matched_file")
        source = Path(source_value).resolve() if source_value else None
        if enable_rename:
            target_name = _safe_relative_path(
                image.get("working_filename") or image.get("original") or f"{uid}.jpg",
                field="working_filename",
            )
        else:
            target_name = _safe_relative_path(
                image.get("original") or (source.name if source else f"{uid}.jpg"),
                field="original",
            )
        destination = (working / Path(target_name)).resolve()
        destination_key = str(destination).casefold()
        disposition = "SKIPPED"
        detail = ""

        prior_uid = destinations.get(destination_key)
        if prior_uid and prior_uid != uid:
            if collision_policy == "disambiguate_with_uid":
                token = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:8]
                target_path = Path(target_name)
                target_name = str(
                    target_path.with_name(
                        f"{target_path.stem}-{token}{target_path.suffix}"
                    )
                ).replace("\\", "/")
                destination = (working / Path(target_name)).resolve()
                destination_key = str(destination).casefold()
                if destination_key in destinations:
                    disposition = "TARGET_COLLISION"
                    detail = (
                        "UID disambiguation still produced a duplicate destination."
                    )
                else:
                    destinations[destination_key] = uid
            else:
                disposition = "TARGET_COLLISION"
                detail = f"Destination collides with Image UID {prior_uid}."
        else:
            destinations[destination_key] = uid

        status = match.get("status", "EXPECTED_NOT_PRESENT")
        if disposition != "TARGET_COLLISION":
            if (
                status == "READY"
                and source is not None
                and claimed[str(source).casefold()] > 1
            ):
                disposition = "AMBIGUOUS_SOURCE"
                detail = "One physical source matched more than one Image UID."
            elif status == "READY" and source is not None:
                if destination.is_file():
                    if _sha256(source) == _sha256(destination):
                        disposition = "UNCHANGED_CURRENT"
                        detail = "Target content matches source."
                    else:
                        disposition = "TARGET_COLLISION"
                        detail = "Existing target differs; refusing overwrite."
                else:
                    disposition = (
                        "WOULD_COPY_RENAMED"
                        if preview_only and enable_rename
                        else "WOULD_COPY_ORIGINAL_NAME"
                        if preview_only
                        else "COPIED_RENAMED"
                        if enable_rename
                        else "COPIED_ORIGINAL_NAME"
                    )
                    detail = "Copy is planned." if preview_only else "Copy pending."
            elif status == "AMBIGUOUS":
                disposition = "AMBIGUOUS_SOURCE"
                detail = f"Multiple source candidates: {match.get('candidates', [])}"
            elif status == "EXPECTED_NOT_PRESENT":
                disposition = "EXPECTED_NOT_PRESENT"
                detail = "Expected by V10 but no physical source is present."

        raw_path = (
            _relative_to_root(source, root)
            if source is not None
            else f"Raw/{session_uid}/{image.get('original') or ''}".rstrip("/")
        )
        plans.append(
            {
                "image_uid": uid,
                "session_uid": session_uid,
                "raw_path": raw_path,
                "working_path": destination.relative_to(root).as_posix(),
                "raw_abs_path": str(source) if source else None,
                "working_abs_path": str(destination),
                "disposition": disposition,
                "disposition_detail": detail,
            }
        )

    if not preview_only:
        for plan in plans:
            if plan["disposition"] not in {
                "COPIED_RENAMED",
                "COPIED_ORIGINAL_NAME",
            }:
                continue
            try:
                _atomic_copy(Path(plan["raw_abs_path"]), Path(plan["working_abs_path"]))
                plan["disposition_detail"] = "Copied atomically to Working."
            except OSError as exc:
                plan["disposition"] = "COPY_FAILED"
                plan["disposition_detail"] = str(exc)

    clean_plans = [
        {
            key: plan[key]
            for key in (
                "image_uid",
                "session_uid",
                "raw_path",
                "working_path",
                "disposition",
                "disposition_detail",
            )
        }
        for plan in plans
    ]
    conversion_text = generate_conversion_map_text(project_model, clean_plans, root)
    conversion_path = root / "Metadata" / "image_name_conversions.txt"
    if write_conversion_map and not preview_only:
        _write_conversion_map(conversion_path, conversion_text)

    counts = Counter(plan["disposition"] for plan in plans)
    return {
        "contract_version": 1,
        "preview_only": preview_only,
        "project_root": str(root),
        "raw_root": str(raw),
        "working_root": str(working),
        "conversion_map_path": conversion_path.relative_to(root).as_posix(),
        "conversion_map_text": conversion_text,
        "summary": {
            "total_expected": len(plans),
            "dispositions": dict(sorted(counts.items())),
            "ready_to_copy_count": counts["WOULD_COPY_RENAMED"]
            + counts["WOULD_COPY_ORIGINAL_NAME"],
            "copied_count": counts["COPIED_RENAMED"] + counts["COPIED_ORIGINAL_NAME"],
            "unchanged_current_count": counts["UNCHANGED_CURRENT"],
            "expected_not_present_count": counts["EXPECTED_NOT_PRESENT"],
            "ambiguous_source_count": counts["AMBIGUOUS_SOURCE"],
            "target_collision_count": counts["TARGET_COLLISION"],
            "copy_failed_count": counts["COPY_FAILED"],
        },
        "images": clean_plans,
        "unmapped_files": reconciliation.get("unmapped_files", []),
    }
