from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "workflow-integrated-prerelease"
DEFAULT_OUTPUT = REPO_ROOT / "dist" / f"{ARCHIVE_ROOT}.zip"

ROOT_RUNTIME_FILES = {
    "runtime-environment.yml",
    "setup_environment.cmd",
    "start_controller.cmd",
    "start_controller_miniforge.cmd",
    "start_custom_matrix.cmd",
}
LEGACY_RUNTIME_FILES = {
    "existing scripts clean/allstrain matrix.py",
    "existing scripts clean/allstrainmatrix extra WT removed.py",
    "existing scripts clean/folder per strain all indiv strains labelled.py",
    "existing scripts clean/make_matrices.py",
    "existing scripts clean/roibox RUN ALL IN PARENT.ijm",
}
SAMPLE_FILES = {
    "examples/grid.example.csv": "samples/grid.csv",
    "examples/images.example.csv": "samples/images.csv",
    "examples/condition_order.example.csv": "samples/condition_order.csv",
    "examples/quick_figure.example.csv": "samples/quick_figure.csv",
}
NON_RUNTIME_TOOL_FILES = {
    "tools/build_portable_release.py",
    "tools/check_image_blind_paths.py",
    "tools/custom_matrix_presentation_preview.py",
    "tools/run_custom_matrix_presentation.py",
}
REQUIRED_ARCHIVE_FILES = {
    "runtime-environment.yml",
    "setup_environment.cmd",
    "start_controller.cmd",
    "start_controller_miniforge.cmd",
    "tools/workflow_controller_extended.py",
    "tools/run_four_point_batch_from_config.py",
    "tools/grid_coordinates.py",
    "tools/finalize_grid_handoff.py",
    "tools/workflow_applets_gui.py",
    "tools/applet_workflows.py",
    "tools/applet_presets.py",
    "tools/annotation_settings_gui.py",
    "tools/quick_figure_gui.py",
    "tools/applets/quick_figure.py",
    "tools/applets/batch_actions.py",
    "tools/applets/v10_adapter.py",
    "tools/applets/culture_crop_export.py",
    "tools/applets/mixed_tier_matrix.py",
    "ahk/four_point_alignment_hotkeys.ah2",
    "existing scripts clean/roibox RUN ALL IN PARENT.ijm",
    "contracts/project_model.schema.json",
    "contracts/grid_coordinate_asset.schema.json",
    "contracts/culture_crop_export.schema.json",
    "contracts/mixed_tier_matrix.schema.json",
    "samples/grid.csv",
    "samples/images.csv",
    "samples/condition_order.csv",
    "samples/quick_figure.csv",
}
BANNED_PARTS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".codex",
    ".agents",
    "docs",
    "tests",
    "fixtures",
    "v10",
}
BANNED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".xlsx",
    ".xls",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}
BANNED_TEXT = re.compile(
    r"(?i)([a-z]:[\\/]+users[\\/]+|/users/|codex|gemini|chatgpt|openai|!scripting|\.git[\\/])"
)
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return {
        item.decode("utf-8").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def release_sources() -> dict[str, Path]:
    selected: dict[str, Path] = {}
    for relative in sorted(tracked_files()):
        destination: str | None = None
        if (
            relative in ROOT_RUNTIME_FILES
            or relative in LEGACY_RUNTIME_FILES
            or (
                (
                    relative.startswith("tools/")
                    and relative.endswith(".py")
                    and relative not in NON_RUNTIME_TOOL_FILES
                )
                or (relative.startswith("ahk/") and relative.endswith(".ah2"))
                or (relative.startswith("contracts/") and relative.endswith(".json"))
                or (relative.startswith("fiji/") and relative.endswith(".ijm"))
            )
        ):
            destination = relative
        if relative in SAMPLE_FILES:
            destination = SAMPLE_FILES[relative]
        if destination:
            selected[destination] = REPO_ROOT / relative
    missing = sorted(REQUIRED_ARCHIVE_FILES - set(selected))
    if missing:
        raise RuntimeError(
            "Release allowlist is missing required files: " + ", ".join(missing)
        )
    return selected


def validate_destination(relative: str) -> None:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive path: {relative}")
    lowered_parts = {part.casefold() for part in path.parts}
    if lowered_parts & BANNED_PARTS:
        raise RuntimeError(f"Forbidden material selected for release: {relative}")
    if path.suffix.casefold() in BANNED_SUFFIXES:
        raise RuntimeError(f"Forbidden file type selected for release: {relative}")


def validate_anonymous_text(relative: str, payload: bytes) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Unexpected non-text runtime file: {relative}") from exc
    match = BANNED_TEXT.search(text)
    if match:
        raise RuntimeError(
            f"Personal/AI/development text found in {relative}: {match.group(0)!r}"
        )
    home_name = Path.home().name.strip()
    if len(home_name) >= 3 and re.search(rf"(?i)\b{re.escape(home_name)}\b", text):
        raise RuntimeError(f"Current user name found in release file: {relative}")
    if EMAIL.search(text):
        raise RuntimeError(f"Email-like text found in release file: {relative}")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_release(output: Path = DEFAULT_OUTPUT) -> Path:
    sources = release_sources()
    payloads: dict[str, bytes] = {}
    for relative, source in sources.items():
        validate_destination(relative)
        payload = source.read_bytes()
        validate_anonymous_text(relative, payload)
        payloads[relative] = payload

    manifest = {
        "format_version": 1,
        "product": "workflow-integrated",
        "release_stage": "pre-release",
        "runtime": "Windows + Miniforge workflow-c + Python 3.11",
        "files": {
            relative: hashlib.sha256(payload).hexdigest()
            for relative, payload in sorted(payloads.items())
        },
    }
    payloads["RELEASE-MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w") as archive:
        for relative, payload in sorted(payloads.items()):
            archive.writestr(zip_info(f"{ARCHIVE_ROOT}/{relative}"), payload)
    os.replace(temporary, output)
    validate_release(output)
    return output


def validate_release(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("Release ZIP contains duplicate paths.")
        prefix = ARCHIVE_ROOT + "/"
        relative_names = {name.removeprefix(prefix) for name in names}
        if any(not name.startswith(prefix) for name in names):
            raise RuntimeError("Release ZIP contains a path outside its product root.")
        missing = sorted(REQUIRED_ARCHIVE_FILES - relative_names)
        if missing:
            raise RuntimeError("Release ZIP is incomplete: " + ", ".join(missing))
        for relative in relative_names:
            validate_destination(relative)
        for name in names:
            validate_anonymous_text(name, archive.read(name))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the anonymous runtime-only pre-release ZIP."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_release(args.output)
    print(output)


if __name__ == "__main__":
    main()
