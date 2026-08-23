from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

try:
    from tools import roi_preset_gui
    from tools import crop_replacement_manifest
    from tools import preflight_batch
    from tools import run_four_point_batch_from_config as batch
except ModuleNotFoundError:
    import roi_preset_gui
    import crop_replacement_manifest
    import preflight_batch
    import run_four_point_batch_from_config as batch


APP_DIR = batch.APP_DIR
PROOF_IMAGES_CSV = APP_DIR / "one_plate_validation_images.csv"
FOUR_POINT_PLATE_MACRO = APP_DIR / "one_plate_four_point.configured.ijm"
REPLACEMENT_MANIFEST = APP_DIR / "one_plate_crop_replacements.tsv"


def open_window_titles() -> list[str]:
    """Return top-level Windows window titles; other platforms need no desktop guard."""
    if sys.platform != "win32":
        return []

    import ctypes

    titles: list[str] = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def collect(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value:
                titles.append(buffer.value)
        return True

    user32.EnumWindows(callback_type(collect), 0)
    return titles


def proof_plate_is_open(filename: str) -> bool:
    """Block only when the exact selected source plate window is already open in Fiji."""
    wanted = Path(filename).name.strip().casefold()
    if not wanted:
        return False
    return any(title.strip().casefold() == wanted for title in open_window_titles())


def read_pending_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise SystemExit(f"Prepared pending-image list not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"Prepared pending-image list has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def choose_pending_row(rows: list[dict[str, str]], filename: str | None = None) -> dict[str, str]:
    if not rows:
        raise SystemExit("No pending images remain for one-plate validation.")
    if filename is None:
        return rows[0]
    wanted = filename.strip()
    matches = [row for row in rows if (row.get("Filename") or "").strip().casefold() == wanted.casefold()]
    if len(matches) != 1:
        available = ", ".join((row.get("Filename") or "").strip() for row in rows[:20])
        raise SystemExit(
            f"Requested validation source {wanted!r} was not found exactly once in the prepared pending list. "
            f"Available pending sources include: {available or 'none'}"
        )
    return matches[0]


def _prepare_completed_plate_macro() -> Path:
    config = batch.load_config(require_fiji=False, require_fiji_handoff_paths=False)
    batch.validate_runtime_files(config, require_fiji=False)
    batch.validate_csvs(config)
    batch.validate_four_point_grid_widths(config)
    batch.ensure_crop_output_root(config)
    return batch.build_four_point_macro(config)


def write_one_row_csv(path: Path, fieldnames: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def patch_prepared_macro(
    source: str,
    proof_csv: Path,
    replacement_manifest: Path | None = None,
    source_folder: str | None = None,
) -> str:
    import re

    old = f'imagesFile = "{batch.macro_path(batch.PENDING_IMAGES_CSV)}";'
    new = f'imagesFile = "{batch.macro_path(proof_csv)}";'
    if source.count(old) != 1:
        raise SystemExit(
            "Prepared macro no longer contains exactly one pending-images path; refusing to guess where to patch."
        )
    source = source.replace(old, new, 1)
    if source_folder is not None:
        old_folders = "folders = getFileList(inputRoot);"
        new_folders = f'folders = newArray("{source_folder}/");'
        if source.count(old_folders) != 1:
            raise SystemExit("Prepared macro has no unambiguous source-folder loop to scope.")
        source = source.replace(old_folders, new_folders, 1)
    if replacement_manifest is not None:
        old_manifest = 'replacementManifest = "";'
        new_manifest = f'replacementManifest = "{batch.macro_path(replacement_manifest)}";'
        if source.count(old_manifest) != 1:
            raise SystemExit("Prepared macro has no unambiguous replacement-manifest setting.")
        source = source.replace(old_manifest, new_manifest, 1)
    # A one-plate proof narrows the metadata file to the selected plate, but it
    # must finish the immediate source-folder loop so Fiji logs every other
    # plate's current state. Remove an old early-stop patch if present.
    source, substitutions = re.subn(
        r'(File\.append\(stateKey \+ "\\t" \+ runNumber \+ "\\n", stateFile\);\s*)'
        r'(?:exit\(\);\s*)?'
        r'(print\([\s\S]*?\);\s*)',
        r"\1\2",
        source,
        count=1,
    )
    if substitutions == 0:
        # Compatibility with compact fixture/older generated macros that do
        # not yet have persistent run-state logging.
        source, substitutions = re.subn(
            r"(processedImages\+\+;)\s*(print\()",
            r"\1\n        \2",
            source,
            count=1,
        )
    if substitutions != 1:
        raise SystemExit("Prepared one-plate macro no longer has one unambiguous post-export completion point.")
    return source





def ensure_roi_click_patch(fiji: Path) -> bool:
    candidates = roi_preset_gui.find_roi_click_tools(fiji.resolve().parent)
    if not candidates:
        raise SystemExit(
            "ROI 1-click Tools was not found in the configured Fiji installation. Install/select Roi 1-Click Tools first."
        )
    if len(candidates) != 1:
        shown = "\n".join(str(path) for path in candidates)
        raise SystemExit(
            "More than one Roi 1-Click Tools macro was found; refusing to guess which Fiji toolset to patch. "
            f"Use ROI presets to select/repair the intended toolset.\n{shown}"
        )
    try:
        return roi_preset_gui.patch_roi_click_tools(candidates[0]) is not None
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Could not patch ROI 1-click Tools safely: {exc}") from exc


def prepare(filename: str | None = None, *, rerun_done: bool = False, replace_existing: bool = False) -> tuple[Path, dict[str, str]]:
    args = [sys.executable, str(Path(batch.__file__).resolve()), "--prepare-only"]
    configured = batch.CONFIGURED_FOUR_POINT_MACRO
    proof_macro = FOUR_POINT_PLATE_MACRO

    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        if (rerun_done or filename) and "All expected crops already exist" in output:
            configured = _prepare_completed_plate_macro()
        else:
            raise SystemExit(output or "Batch preparation failed before one-plate validation.")

    fieldnames, rows = read_pending_rows(batch.PENDING_IMAGES_CSV)
    if rerun_done or replace_existing:
        config = batch.load_config(require_fiji=False, require_fiji_handoff_paths=False)
        fieldnames, authoritative_rows = read_pending_rows(Path(config["images_csv"]))
        selected = choose_pending_row(authoritative_rows, filename)
        configured = _prepare_completed_plate_macro()
    else:
        selected = choose_pending_row(rows, filename)
    write_one_row_csv(PROOF_IMAGES_CSV, fieldnames, selected)

    if not configured.is_file():
        raise SystemExit(f"Prepared macro not found: {configured}")
    # build_four_point_macro() is the source of truth for the complete current
    # four-point interaction. The proof only narrows its metadata input.
    config = batch.load_config(require_fiji=False, require_fiji_handoff_paths=False)
    matching_sources = [
        item
        for item in preflight_batch.discover_sources(Path(config["image_root"]))
        if item.name.casefold() == selected["Filename"].casefold()
    ]
    if len(matching_sources) != 1:
        raise SystemExit(f"Selected source is not uniquely present under image_root: {selected['Filename']}")
    manifest = None
    if replace_existing:
        crop_replacement_manifest.write_manifest(config, selected, REPLACEMENT_MANIFEST)
        manifest = REPLACEMENT_MANIFEST
    proof_text = patch_prepared_macro(
        configured.read_text(encoding="utf-8"),
        PROOF_IMAGES_CSV,
        manifest,
        matching_sources[0].parent.name,
    )
    proof_macro.write_text(proof_text, encoding="utf-8")
    return proof_macro, selected


def run_with_process(
    filename: str | None = None,
    *,
    rerun_done: bool = False,
    replace_existing: bool = False,
) -> tuple[dict[str, str], subprocess.Popen]:
    """Launch one proof and return the controller-owned Fiji process."""
    if filename and proof_plate_is_open(filename):
        raise SystemExit(
            f"The selected proof plate is already open in Fiji: {Path(filename).name}. "
            "Finish or close that plate before launching the same proof again. Other open Fiji images do not block this action."
        )

    config = batch.load_config(require_fiji=True, require_fiji_handoff_paths=False)
    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")

    if ensure_roi_click_patch(fiji):
        raise SystemExit(
            "ROI 1-click Tools was patched successfully so its saved rectangle and click-behaviour settings are restored automatically. "
            "Close/restart Fiji once so it reloads the patched toolset, then run the proof again."
        )

    macro, selected = prepare(filename, rerun_done=rerun_done, replace_existing=replace_existing)
    command = [str(fiji), "--no-splash", "-macro", str(macro)]
    try:
        process = subprocess.Popen(command, cwd=fiji.parent)
    except OSError as exc:
        raise SystemExit(f"Could not launch Fiji one-plate validation: {exc}") from exc
    return selected, process


def run(filename: str | None = None, *, rerun_done: bool = False, replace_existing: bool = False) -> dict[str, str]:
    """Backward-compatible one-plate launcher for command-line callers."""
    selected, _process = run_with_process(
        filename,
        rerun_done=rerun_done,
        replace_existing=replace_existing,
    )
    return selected


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Launch exactly one selected pending source image for validation.")
    parser.add_argument("--filename", help="exact pending source filename; default is the first authoritative pending row")
    args = parser.parse_args()
    selected = run(args.filename)
    print(
        "Launched one-plate four-point alignment: "
        f"{selected.get('Filename', '')} | {selected.get('Experiment', '')}/"
        f"{selected.get('Set', '')}/{selected.get('Type', '')}"
    )


if __name__ == "__main__":
    main()
