from __future__ import annotations

import os
from pathlib import Path

TOOLSET_NAME = "Roi 1-Click Tools.ijm"
BACKUP_SUFFIX = ".workflow-backup"
PATCH_MARKER = "// cautious-rotary-phone: restore saved ROI 1-click settings on every click"
ROTATED_TOOL_SIGNATURE = 'macro "Rotated Rectangle Click Tool - Cf00R11cc" {'

RESTORE_BLOCK = '''macro "Rotated Rectangle Click Tool - Cf00R11cc" {
	// cautious-rotary-phone: restore saved ROI 1-click settings on every click
	// Upstream otherwise keeps stock in-memory defaults until its Options dialog is opened.
	rotRectWidth  = call("ij.Prefs.get", "rect.width", rotRectWidth);
	rotRectHeight = call("ij.Prefs.get", "rect.height", rotRectHeight);
	rotRectAngle  = call("ij.Prefs.get", "rect.angle", rotRectAngle);
	addToManager = call("ij.Prefs.get", "default.addToManager", addToManager);
	runMeasure   = call("ij.Prefs.get", "default.runMeasure", runMeasure);
	doNextSlice  = call("ij.Prefs.get", "default.doNextSlice", doNextSlice);
	dimension    = call("ij.Prefs.get", "default.dimension", dimension);
	doExtraCmd   = call("ij.Prefs.get", "default.doExtraCmd", doExtraCmd);
	extraCmd     = call("ij.Prefs.get", "default.extraCmd", extraCmd);
'''


def toolset_path_from_fiji(fiji_executable: Path) -> Path:
    return fiji_executable.resolve().parent / "macros" / "toolsets" / TOOLSET_NAME


def patch_text(source: str) -> tuple[str, bool]:
    if PATCH_MARKER in source:
        return source, False
    if source.count(ROTATED_TOOL_SIGNATURE) != 1:
        raise ValueError(
            "Installed ROI 1-click toolset no longer contains exactly one expected Rotated Rectangle Click Tool; "
            "refusing to patch an unknown version."
        )
    return source.replace(ROTATED_TOOL_SIGNATURE, RESTORE_BLOCK, 1), True


def ensure_patched(fiji_executable: Path) -> tuple[Path, bool]:
    toolset = toolset_path_from_fiji(fiji_executable)
    if not toolset.is_file():
        raise SystemExit(
            "ROI 1-click toolset was not found beside the configured Fiji installation: "
            f"{toolset}. Install ROI 1-click Tools in Fiji first."
        )

    try:
        source = toolset.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Could not read ROI 1-click toolset {toolset}: {exc}") from exc

    try:
        patched, changed = patch_text(source)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not changed:
        return toolset, False

    backup = toolset.with_name(toolset.name + BACKUP_SUFFIX)
    try:
        if not backup.exists():
            backup.write_text(source, encoding="utf-8")
        temporary = toolset.with_name(toolset.name + ".workflow-new")
        temporary.write_text(patched, encoding="utf-8")
        os.replace(temporary, toolset)
    except OSError as exc:
        raise SystemExit(
            "Could not install the small ROI 1-click preference-restoration patch. "
            f"No further Fiji changes were attempted. Target: {toolset}. Error: {exc}"
        ) from exc

    return toolset, True
