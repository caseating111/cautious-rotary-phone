from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MACRO = REPO_ROOT / "existing scripts clean" / "roibox RUN ALL IN PARENT.ijm"
ALIGNMENT_MACRO = REPO_ROOT / "fiji" / "full_column_alignment.ijm"
CROP_HELPER = REPO_ROOT / "fiji" / "export_crops_from_alignment.ijm"
VALIDATOR = REPO_ROOT / "tools" / "validate_project_csvs.py"
PREFLIGHT = REPO_ROOT / "tools" / "preflight_batch.py"
PREFLIGHT_REPORT = APP_DIR / "last_preflight.txt"
PENDING_IMAGES_CSV = APP_DIR / "pending_images.csv"
CONFIGURED_MACRO = APP_DIR / "batch_full_column.configured.ijm"

START_MARKER = "        // ====================================================\n        // IDENTIFY CURRENT PLATE"
END_MARKER = "        setBatchMode(false);"


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = [
        "fiji_executable",
        "image_root",
        "crop_output",
        "grid_csv",
        "images_csv",
        "condition_order_csv",
    ]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))

    try:
        data["alignment_tolerance"] = float(data.get("alignment_tolerance", 0.08))
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid processing setting: {exc}") from exc
    if data["alignment_tolerance"] <= 0 or data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Alignment tolerance and crop dimensions must be positive.")
    return data


def validate_csvs(config: dict) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            str(config["grid_csv"]),
            str(config["images_csv"]),
            str(config["condition_order_csv"]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        raise SystemExit(output or "CSV validation failed.")


def run_preflight() -> int:
    result = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),
            "--report",
            str(PREFLIGHT_REPORT),
            "--pending-images-csv",
            str(PENDING_IMAGES_CSV),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise SystemExit(output or f"Batch preflight failed. See {PREFLIGHT_REPORT}")

    with PENDING_IMAGES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        pending = sum(1 for _ in csv.DictReader(handle))
    if pending == 0:
        raise SystemExit(f"All expected crops already exist. See {PREFLIGHT_REPORT}")
    return pending


def macro_path(value: str | Path) -> str:
    return str(Path(value)).replace("\\", "/").replace('"', '\\"')


def replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one source setting, found {count}: {old}")
    return source.replace(old, new, 1)


def build_macro(config: dict) -> Path:
    source = SOURCE_MACRO.read_text(encoding="utf-8")

    replacements = {
        'gridFile   = "path here";': f'gridFile   = "{macro_path(config["grid_csv"])}";',
        'imagesFile = "path here";': f'imagesFile = "{macro_path(PENDING_IMAGES_CSV)}";',
        'inputRoot  = "path here";': f'inputRoot  = "{macro_path(config["image_root"])}";',
        'outputRoot = "path here";': f'outputRoot = "{macro_path(config["crop_output"])}";',
        "CROP_W = 130;": f'CROP_W = {config["crop_width"]};',
        "CROP_H = 546;": f'CROP_H = {config["crop_height"]};',
    }
    for old, new in replacements.items():
        source = replace_once(source, old, new)

    if source.count(START_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise SystemExit("Production macro calibration markers changed; refusing to guess where to patch.")

    start = source.index(START_MARKER)
    end = source.index(END_MARKER, start) + len(END_MARKER)

    composed = f'''        // ====================================================
        // FULL-COLUMN COMPOSED ROUTE
        // Existing folder/CSV lookup above and close/logging below are preserved.
        // Completed images were removed from the temporary metadata preflight.
        // ====================================================

        showMessage(
            "Next plate",
            "Folder: " + cleanFolderName + "\\n\\n" +
            "Image: " + sourceTitle + "\\n\\n" +
            "Experiment: " + experiment + "\\n" +
            "Set: " + setName + "\\n" +
            "Type: " + typeName + "\\n" +
            "Grid: 8 x " + gridCols + "\\n" +
            "Exports: " + (nWanted * 2) + "\\n\\n" +
            "Next: position the FIRST and LAST whole-column ROIs."
        );

        runMacro(
            "{macro_path(ALIGNMENT_MACRO)}",
            "cols=" + gridCols + ";rows=8;tolerance={config['alignment_tolerance']}"
        );

        runMacro(
            "{macro_path(CROP_HELPER)}",
            "grid_csv={macro_path(config['grid_csv'])};" +
            "output_dir=" + outDir + ";" +
            "experiment=" + experiment + ";" +
            "set=" + setName + ";" +
            "type=" + typeName + ";" +
            "crop_w=" + CROP_W + ";crop_h=" + CROP_H
        );'''

    source = source[:start] + composed + source[end:]
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_MACRO.write_text(source, encoding="utf-8")
    return CONFIGURED_MACRO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="validate/preflight and build the configured Fiji macro without launching Fiji",
    )
    args = parser.parse_args()

    config = load_config()
    validate_csvs(config)
    pending = run_preflight()
    macro = build_macro(config)

    if args.prepare_only:
        print(f"Prepared composed batch for {pending} pending image(s): {macro}")
        return

    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    subprocess.Popen([str(fiji), "-macro", str(macro)])


if __name__ == "__main__":
    main()
