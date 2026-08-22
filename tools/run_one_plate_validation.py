from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

try:
    from tools import run_full_column_batch_from_config as batch
except ModuleNotFoundError:
    import run_full_column_batch_from_config as batch


APP_DIR = batch.APP_DIR
PROOF_IMAGES_CSV = APP_DIR / "one_plate_validation_images.csv"
PROOF_MACRO = APP_DIR / "one_plate_validation.configured.ijm"
PROOF_LEGACY_MACRO = APP_DIR / "one_plate_four_point_validation.configured.ijm"
_ACTIVE_FIJI_PROCESS: subprocess.Popen | None = None


def proof_is_running() -> bool:
    """Compatibility helper only; a live Fiji app is not treated as a live proof."""
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
    matches = [row for row in rows if (row.get("Filename") or "").strip() == wanted]
    if len(matches) != 1:
        available = ", ".join((row.get("Filename") or "").strip() for row in rows[:20])
        raise SystemExit(
            f"Requested validation source {wanted!r} was not found exactly once in the prepared pending list. "
            f"Available pending sources include: {available or 'none'}"
        )
    return matches[0]


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
            '            "A temporary boosted alignment view will open. The ROI 1-click Rotated Rectangle Click Tool will be selected automatically for the four colony-centre clicks."',
        ),
        (
            '        run("Enhance Contrast", "saturated=0.35");\n\n'
            '        CLICK_ROI = 108;\n'
            '        accepted = 0;\n'
            '        makeRectangle(round(viewW / 2 - CLICK_ROI / 2), round(viewH / 2 - CLICK_ROI / 2), CLICK_ROI, CLICK_ROI);',
            '        run("Enhance Contrast", "saturated=0.35");\n'
            '        run("Select None");\n'
            '        setTool("Rotated Rectangle Click Tool - Cf00R11cc");\n\n'
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
            '            R1LX = x + w / 2;\n            R1LY = y + h / 2;',
            '            R1LX = x + w / 2;\n            R1LY = y + h / 2;\n            QC_W = w;\n            QC_H = h;',
        ),
        (
            '                    Overlay.drawRect(qcX - CLICK_ROI / 2, qcY - CLICK_ROI / 2, CLICK_ROI, CLICK_ROI);',
            '                    Overlay.drawRect(qcX - QC_W / 2, qcY - QC_H / 2, QC_W, QC_H);',
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


def prepare(filename: str | None = None, *, legacy: bool = False) -> tuple[Path, dict[str, str]]:
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
        raise SystemExit(output or "Batch preparation failed before one-plate validation.")

    fieldnames, rows = read_pending_rows(batch.PENDING_IMAGES_CSV)
    selected = choose_pending_row(rows, filename)
    write_one_row_csv(PROOF_IMAGES_CSV, fieldnames, selected)

    if not configured.is_file():
        raise SystemExit(f"Prepared macro not found: {configured}")
    proof_text = patch_prepared_macro(configured.read_text(encoding="utf-8"), PROOF_IMAGES_CSV)
    if legacy:
        proof_text = patch_roi_click_interaction(proof_text)
    proof_macro.write_text(proof_text, encoding="utf-8")
    return proof_macro, selected


def run(filename: str | None = None, *, legacy: bool = False) -> dict[str, str]:
    global _ACTIVE_FIJI_PROCESS

    if filename and proof_plate_is_open(filename):
        raise SystemExit(
            f"The selected proof plate is already open in Fiji: {Path(filename).name}. "
            "Finish or close that plate before launching the same proof again. Other open Fiji images do not block this action."
        )

    macro, selected = prepare(filename, legacy=legacy)
    config = batch.load_config(require_fiji=True, require_fiji_handoff_paths=not legacy)
    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    try:
        _ACTIVE_FIJI_PROCESS = subprocess.Popen([str(fiji), "-macro", str(macro)])
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
