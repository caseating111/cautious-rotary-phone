from __future__ import annotations

import json
import subprocess
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MACRO = REPO_ROOT / "existing scripts clean" / "roibox RUN ALL IN PARENT.ijm"
ALIGNMENT_MACRO = REPO_ROOT / "fiji" / "full_column_alignment.ijm"
CROP_HELPER = REPO_ROOT / "fiji" / "export_crops_from_alignment.ijm"
CONFIGURED_MACRO = APP_DIR / "batch_full_column.configured.ijm"

START_MARKER = "        // ====================================================\n        // IDENTIFY CURRENT PLATE"
END_MARKER = "        setBatchMode(false);"


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = ["fiji_executable", "image_root", "crop_output", "grid_csv", "images_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


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
        'imagesFile = "path here";': f'imagesFile = "{macro_path(config["images_csv"])}";',
        'inputRoot  = "path here";': f'inputRoot  = "{macro_path(config["image_root"])}";',
        'outputRoot = "path here";': f'outputRoot = "{macro_path(config["crop_output"])}";',
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
            "cols=" + gridCols + ";rows=8;tolerance=0.08"
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
    config = load_config()
    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    macro = build_macro(config)
    subprocess.Popen([str(fiji), "-macro", str(macro)])


if __name__ == "__main__":
    main()
