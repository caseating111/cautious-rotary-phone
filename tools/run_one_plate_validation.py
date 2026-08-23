from __future__ import annotations

import csv
import getpass
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

try:
    from tools import roi_preset_gui
    from tools import run_full_column_batch_from_config as batch
except ModuleNotFoundError:
    import roi_preset_gui
    import run_full_column_batch_from_config as batch


APP_DIR = batch.APP_DIR
PROOF_IMAGES_CSV = APP_DIR / "one_plate_validation_images.csv"
PROOF_MACRO = APP_DIR / "one_plate_validation.configured.ijm"
PROOF_LEGACY_MACRO = APP_DIR / "one_plate_four_point_validation.configured.ijm"
PROOF_STATUS_FILE = APP_DIR / "one_plate_four_point_validation.status.txt"
PROOF_LAUNCH_LOG = APP_DIR / "one_plate_four_point_validation.launch.log"
_ACTIVE_FIJI_PROCESS: subprocess.Popen | None = None


def proof_is_running() -> bool:
    """Compatibility helper; an open Fiji session does not block proof runs."""
    return False


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


def _is_fiji_main_title(title: str) -> bool:
    folded = title.strip().casefold()
    return (
        folded == "fiji"
        or folded == "imagej"
        or folded == "(fiji is just) imagej"
        or folded.startswith("fiji (")
        or ("fiji" in folded and folded.endswith("imagej"))
    )


def fiji_is_open() -> bool:
    """Best-effort detection of the legacy Fiji/ImageJ main toolbar window on Windows."""
    return any(_is_fiji_main_title(title) for title in open_window_titles())


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


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    return read_pending_rows(path)


def source_dispositions(config: dict, selected_filename: str) -> list[str]:
    """Give every physical image in the macro's immediate-subfolder scope a decision."""
    _, metadata = read_csv_rows(Path(config["images_csv"]))
    _, pending = read_pending_rows(batch.PENDING_IMAGES_CSV)
    listed = {(row.get("Filename") or "").strip().casefold() for row in metadata}
    pending_names = {(row.get("Filename") or "").strip().casefold() for row in pending}
    selected = selected_filename.strip().casefold()
    image_root = Path(config["image_root"])
    extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    decisions: list[str] = []
    for folder in sorted((path for path in image_root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold()):
        for path in sorted((path for path in folder.iterdir() if path.is_file()), key=lambda path: path.name.casefold()):
            if path.suffix.casefold() not in extensions:
                continue
            key = path.name.casefold()
            if key == selected:
                state = "ACTIVE"
            elif key in pending_names:
                state = "PENDING"
            elif key in listed:
                state = "DONE"
            else:
                state = "NOT_LISTED"
            decisions.append(f"{state}: {folder.name}/{path.name}")
    return decisions


def patch_invocation_guard(source: str, token: str) -> str:
    status_path = batch.macro_path(PROOF_STATUS_FILE)
    start_marker = "gridText = File.openAsString(gridFile);"
    finish_marker = '// ============================================================\n// FINISHED\n// ============================================================'
    if source.count(start_marker) != 1 or source.count(finish_marker) != 1:
        raise SystemExit("Prepared proof no longer has unique lifecycle guard insertion points.")
    guard = (
        f'proofStatusFile = "{status_path}";\n'
        f'proofToken = "{token}";\n'
        'proofStatus = String.trim(File.openAsString(proofStatusFile));\n'
        'if (proofStatus != "READY " + proofToken)\n'
        '    exit("Duplicate or stale one-plate proof invocation ignored.");\n'
        'File.saveString("RUNNING " + proofToken, proofStatusFile);\n\n'
    )
    finish = f'File.saveString("DONE {token}", proofStatusFile);\n\n{finish_marker}'
    return source.replace(start_marker, guard + start_marker, 1).replace(finish_marker, finish, 1)


def arm_invocation(macro: Path, token: str) -> None:
    guarded = patch_invocation_guard(macro.read_text(encoding="utf-8"), token)
    macro.write_text(guarded, encoding="utf-8")
    PROOF_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROOF_STATUS_FILE.write_text(f"READY {token}", encoding="utf-8")


def _prepare_completed_plate_macro(*, legacy: bool) -> Path:
    config = batch.load_config(require_fiji=False, require_fiji_handoff_paths=not legacy)
    batch.validate_runtime_files(config, require_fiji=False, legacy=legacy)
    batch.validate_csvs(config)
    if legacy:
        batch.validate_legacy_grid_widths(config)
    batch.ensure_crop_output_root(config)
    return batch.build_legacy_macro(config) if legacy else batch.build_macro(config)


def write_one_row_csv(path: Path, fieldnames: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def patch_prepared_macro(source: str, proof_csv: Path) -> str:
    old = f'imagesFile = "{batch.macro_path(batch.PENDING_IMAGES_CSV)}";'
    new = f'imagesFile = "{batch.macro_path(proof_csv)}";'
    if source.count(old) != 1:
        raise SystemExit(
            "Prepared macro no longer contains exactly one pending-images path; refusing to guess where to patch."
        )
    return source.replace(old, new, 1)


def patch_roi_click_interaction(source: str) -> str:
    """Let installed ROI 1-click tools provide the click ROI; keep only geometry/QC here."""
    replacements = [
        (
            '            "A temporary boosted alignment view will open. Centre the 108x108 box four times."',
            '            "A temporary CLAHE alignment view will open. The ROI 1-click Rotated Rectangle Click Tool will be selected automatically for the four colony-centre clicks."',
        ),
        (
            '        getDimensions(viewW, viewH, viewC, viewZ, viewT);\n'
            '        sampleW = round(viewW * 0.30);\n'
            '        sampleH = round(viewH * 0.30);\n'
            '        sampleX = round((viewW - sampleW) / 2);\n'
            '        sampleY = round((viewH - sampleH) / 2);\n'
            '        makeRectangle(sampleX, sampleY, sampleW, sampleH);\n'
            '        run("Enhance Contrast", "saturated=0.35");\n\n'
            '        CLICK_ROI = 108;\n'
            '        accepted = 0;\n'
            '        makeRectangle(round(viewW / 2 - CLICK_ROI / 2), round(viewH / 2 - CLICK_ROI / 2), CLICK_ROI, CLICK_ROI);',
            '        getDimensions(viewW, viewH, viewC, viewZ, viewT);\n'
            '        // Alignment visibility only: run the user-tested CLAHE settings\n'
            '        // twice across the ENTIRE disposable alignment image. No temporary\n'
            '        // sampling ROI is needed for CLAHE. Explicitly clear any ROI copied\n'
            '        // into the duplicate because CLAHE respects active selections.\n'
            '        run("Select None");\n'
            '        // call() always returns a string; convert saved ROI dimensions once,\n'
            '        // at their source, before CLAHE or QC arithmetic uses them.\n'
            '        roiBoxW = parseFloat(call("ij.Prefs.get", "rect.width", 108));\n'
            '        roiBoxH = parseFloat(call("ij.Prefs.get", "rect.height", 108));\n'
            '        roiBoxSize = maxOf(roiBoxW, roiBoxH);\n'
            '        claheBlock = round(roiBoxSize * 3.3);\n'
            '        if (claheBlock < 1) claheBlock = 356;\n'
            '        claheOptions = "blocksize=" + claheBlock + " histogram=256 maximum=1000 mask=*None* fast_(less_accurate)";\n'
            '        run("Enhance Local Contrast (CLAHE)", claheOptions);\n'
            '        run("Enhance Local Contrast (CLAHE)", claheOptions);\n\n'
            '        // Reload/install the already-present ROI 1-click toolset.\n'
            '        roiToolsetPath = getDirectory("macros") + "toolsets/Roi 1-Click Tools.ijm";\n'
            '        if (File.exists(roiToolsetPath))\n'
            '            run("Install...", "install=[" + roiToolsetPath + "]");\n\n'
            '        // The launcher and AHK position the existing ImageJ frame. Do not call\n'
            '        // Window Organizer > Show All here: forwarded single-instance macros can\n'
            '        // run while IJ.getInstance() is null, and that command dereferences it.\n\n'
            '        roiClickToolFound = 0;\n'
            '        for (toolCandidate = 15; toolCandidate <= 21; toolCandidate++) {\n'
            '            setTool(toolCandidate);\n'
            '            if (startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")) {\n'
            '                roiClickToolFound = 1;\n'
            '                break;\n'
            '            }\n'
            '        }\n'
            '        if (roiClickToolFound == 0)\n'
            '            showMessage("ROI 1-click", "The Rotated Rectangle Click Tool could not be selected automatically. The Fiji toolbar is visible so you can select it manually, then continue.");\n\n'
            '        QC_W = roiBoxW;\n'
            '        QC_H = roiBoxH;\n'
            '        accepted = 0;',
        ),
        (
            '                sourceTitle + "\\n\\nCentre box on ROW 1, COLUMN 1.\\n\\nReposition as needed, then click OK."',
            '                sourceTitle + "\\n\\nClick the centre of ROW 1, COLUMN 1 with the ROI 1-click Rotated Rectangle Click Tool, then click OK."',
        ),
        (
            '                sourceTitle + "\\n\\nCentre box on ROW 1, COLUMN " + gridCols + ".\\n\\nReposition as needed, then click OK."',
            '                sourceTitle + "\\n\\nClick the centre of ROW 1, COLUMN " + gridCols + " with the ROI 1-click Rotated Rectangle Click Tool, then click OK."',
        ),
        (
            '                sourceTitle + "\\n\\nCentre box on ROW 5, COLUMN 1.\\n\\nReposition as needed, then click OK."',
            '                sourceTitle + "\\n\\nClick the centre of ROW 5, COLUMN 1 with the ROI 1-click Rotated Rectangle Click Tool, then click OK."',
        ),
        (
            '                sourceTitle + "\\n\\nCentre box on ROW 5, COLUMN " + gridCols + ".\\n\\nReposition as needed, then click OK."',
            '                sourceTitle + "\\n\\nClick the centre of ROW 5, COLUMN " + gridCols + " with the ROI 1-click Rotated Rectangle Click Tool, then click OK."',
        ),
        (
            '            // Pure mathematical 8 x N lattice from the four authoritative centres.\n'
            '            Overlay.remove;\n'
            '            setColor("cyan");\n'
            '            for (qcRow = 1; qcRow <= 8; qcRow++) {',
            '            // Pure mathematical 8 x N lattice from the four authoritative centres.\n'
            '            // Derive the two plate axes from the four clicks so QC boxes and\n'
            '            // lattice lines rotate/skew with the actual plate instead of staying\n'
            '            // screen-axis aligned.\n'
            '            gridHX = ((R1RX - R1LX) + (R5RX - R5LX)) / 2;\n'
            '            gridHY = ((R1RY - R1LY) + (R5RY - R5LY)) / 2;\n'
            '            gridVX = ((R5LX - R1LX) + (R5RX - R1RX)) / 2;\n'
            '            gridVY = ((R5LY - R1LY) + (R5RY - R1RY)) / 2;\n'
            '            hLen = sqrt(gridHX * gridHX + gridHY * gridHY);\n'
            '            vLen = sqrt(gridVX * gridVX + gridVY * gridVY);\n'
            '            if (hLen <= 0 || vLen <= 0)\n'
            '                exit("Four-point geometry collapsed to a zero-length grid axis.");\n'
            '            hux = gridHX / hLen;\n'
            '            huy = gridHY / hLen;\n'
            '            vux = gridVX / vLen;\n'
            '            vuy = gridVY / vLen;\n'
            '            Overlay.remove;\n'
            '            setColor("cyan");\n'
            '            for (qcRow = 1; qcRow <= 8; qcRow++) {',
        ),
        (
            '                for (qcCol = 1; qcCol <= gridCols; qcCol++) {\n'
            '                    u = (qcCol - 1) / (gridCols - 1);\n'
            '                    qcX = qcLeftX + u * (qcRightX - qcLeftX);\n'
            '                    qcY = qcLeftY + u * (qcRightY - qcLeftY);\n'
            '                    Overlay.drawRect(qcX - CLICK_ROI / 2, qcY - CLICK_ROI / 2, CLICK_ROI, CLICK_ROI);\n'
            '                }\n'
            '            }',
            '                Overlay.drawLine(qcLeftX, qcLeftY, qcRightX, qcRightY);\n'
            '                for (qcCol = 1; qcCol <= gridCols; qcCol++) {\n'
            '                    u = (qcCol - 1) / (gridCols - 1);\n'
            '                    qcX = qcLeftX + u * (qcRightX - qcLeftX);\n'
            '                    qcY = qcLeftY + u * (qcRightY - qcLeftY);\n'
            '                    p1x = qcX - (QC_W / 2) * hux - (QC_H / 2) * vux;\n'
            '                    p1y = qcY - (QC_W / 2) * huy - (QC_H / 2) * vuy;\n'
            '                    p2x = qcX + (QC_W / 2) * hux - (QC_H / 2) * vux;\n'
            '                    p2y = qcY + (QC_W / 2) * huy - (QC_H / 2) * vuy;\n'
            '                    p3x = qcX + (QC_W / 2) * hux + (QC_H / 2) * vux;\n'
            '                    p3y = qcY + (QC_W / 2) * huy + (QC_H / 2) * vuy;\n'
            '                    p4x = qcX - (QC_W / 2) * hux + (QC_H / 2) * vux;\n'
            '                    p4y = qcY - (QC_W / 2) * huy + (QC_H / 2) * vuy;\n'
            '                    Overlay.drawLine(p1x, p1y, p2x, p2y);\n'
            '                    Overlay.drawLine(p2x, p2y, p3x, p3y);\n'
            '                    Overlay.drawLine(p3x, p3y, p4x, p4y);\n'
            '                    Overlay.drawLine(p4x, p4y, p1x, p1y);\n'
            '                }\n'
            '            }\n'
            '            for (qcCol = 1; qcCol <= gridCols; qcCol++) {\n'
            '                u = (qcCol - 1) / (gridCols - 1);\n'
            '                topX = R1LX + u * (R1RX - R1LX);\n'
            '                topY = R1LY + u * (R1RY - R1LY);\n'
            '                bottomLeftX = R1LX + 1.75 * (R5LX - R1LX);\n'
            '                bottomLeftY = R1LY + 1.75 * (R5LY - R1LY);\n'
            '                bottomRightX = R1RX + 1.75 * (R5RX - R1RX);\n'
            '                bottomRightY = R1RY + 1.75 * (R5RY - R1RY);\n'
            '                bottomX = bottomLeftX + u * (bottomRightX - bottomLeftX);\n'
            '                bottomY = bottomLeftY + u * (bottomRightY - bottomLeftY);\n'
            '                Overlay.drawLine(topX, topY, bottomX, bottomY);\n'
            '            }',
        ),
        (
            '            } else {\n                Overlay.remove;\n                makeRectangle(round(R1LX - CLICK_ROI / 2), round(R1LY - CLICK_ROI / 2), CLICK_ROI, CLICK_ROI);\n            }',
            '            } else {\n                Overlay.remove;\n            }',
        ),
    ]
    for old, new in replacements:
        if source.count(old) != 1:
            raise SystemExit("Prepared four-point proof no longer matches the ROI 1-click adapter contract; refusing to guess.")
        source = source.replace(old, new, 1)
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


def prepare(filename: str | None = None, *, legacy: bool = False, rerun_done: bool = False) -> tuple[Path, dict[str, str]]:
    args = [sys.executable, str(Path(batch.__file__).resolve()), "--prepare-only"]
    configured = batch.CONFIGURED_MACRO
    proof_macro = PROOF_MACRO
    if legacy:
        args.append("--legacy")
        configured = batch.CONFIGURED_LEGACY_MACRO
        proof_macro = PROOF_LEGACY_MACRO

    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        if rerun_done and "All expected crops already exist" in output:
            configured = _prepare_completed_plate_macro(legacy=legacy)
        else:
            raise SystemExit(output or "Batch preparation failed before one-plate validation.")

    fieldnames, rows = read_pending_rows(batch.PENDING_IMAGES_CSV)
    if rerun_done:
        config = batch.load_config(require_fiji=False, require_fiji_handoff_paths=not legacy)
        fieldnames, authoritative_rows = read_csv_rows(Path(config["images_csv"]))
        selected = choose_pending_row(authoritative_rows, filename)
    else:
        selected = choose_pending_row(rows, filename)
    write_one_row_csv(PROOF_IMAGES_CSV, fieldnames, selected)

    if not configured.is_file():
        raise SystemExit(f"Prepared macro not found: {configured}")
    # build_legacy_macro() is the source of truth for the complete current
    # four-point interaction. The proof only narrows its metadata input.
    proof_text = patch_prepared_macro(configured.read_text(encoding="utf-8"), PROOF_IMAGES_CSV)
    proof_macro.write_text(proof_text, encoding="utf-8")
    return proof_macro, selected


def run(filename: str | None = None, *, legacy: bool = False, rerun_done: bool = False) -> dict[str, str]:
    global _ACTIVE_FIJI_PROCESS

    if filename and proof_plate_is_open(filename):
        raise SystemExit(
            f"The selected proof plate is already open in Fiji: {Path(filename).name}. "
            "Finish or close that plate before launching the same proof again. Other open Fiji images do not block this action."
        )

    config = batch.load_config(require_fiji=True, require_fiji_handoff_paths=not legacy)
    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")

    if legacy and ensure_roi_click_patch(fiji):
        raise SystemExit(
            "ROI 1-click Tools was patched successfully so its saved rectangle and click-behaviour settings are restored automatically. "
            "Close/restart Fiji once so it reloads the patched toolset, then run the proof again."
        )

    macro, selected = prepare(filename, legacy=legacy, rerun_done=rerun_done)
    command = [str(fiji), "--no-splash", "-macro", str(macro)]
    try:
        _ACTIVE_FIJI_PROCESS = subprocess.Popen(command, cwd=fiji.parent)
    except OSError as exc:
        raise SystemExit(f"Could not launch Fiji one-plate validation: {exc}") from exc
    return selected


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Launch exactly one selected pending source image for validation.")
    parser.add_argument("--filename", help="exact pending source filename; default is the first authoritative pending row")
    parser.add_argument("--legacy", action="store_true", help="use the four-point mathematical alignment route")
    args = parser.parse_args()
    selected = run(args.filename, legacy=args.legacy)
    route = "four-point" if args.legacy else "full-column"
    print(
        f"Launched one-plate {route} validation: "
        f"{selected.get('Filename', '')} | {selected.get('Experiment', '')}/"
        f"{selected.get('Set', '')}/{selected.get('Type', '')}"
    )


if __name__ == "__main__":
    main()
