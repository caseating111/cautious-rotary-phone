from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import preflight_batch
    from tools.validate_project_csvs import validate as validate_csvs
except ModuleNotFoundError:
    import preflight_batch
    from validate_project_csvs import validate as validate_csvs

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
PENDING_IMAGES_CSV = APP_DIR / "pending_images.csv"
CONFIGURED_MACRO = APP_DIR / "batch_full_column.configured.ijm"
CONFIGURED_LEGACY_MACRO = APP_DIR / "batch_four_point_fallback.configured.ijm"
LEGACY_STATE_FILE = APP_DIR / "batch_state.csv"
PREFLIGHT_REPORT = APP_DIR / "last_preflight.txt"
SOURCE_MACRO = REPO_ROOT / "existing scripts clean" / "roibox RUN ALL IN PARENT.ijm"
FULL_COLUMN_MACRO = REPO_ROOT / "fiji" / "full_column_alignment.ijm"

START_MARKER = "        // 1 / 4 — R1C1"
END_MARKER = "        // 4 / 4 — R5C"


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read config: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Config must be a JSON object.")
    return data


def required_path(config: dict, key: str, *, directory: bool = False) -> Path:
    raw = str(config.get(key, "")).strip()
    if not raw:
        raise SystemExit(f"Missing configured path: {key}")
    path = Path(raw)
    if directory:
        if not path.is_dir():
            raise SystemExit(f"Configured {key} is not a directory: {path}")
    elif not path.is_file():
        raise SystemExit(f"Configured {key} is not a file: {path}")
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_pending_images(rows: list[dict[str, str]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = ["Filename", "Experiment", "Set", "Type"]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def source_image_paths(image_root: Path) -> dict[str, list[Path]]:
    mapped: dict[str, list[Path]] = {}
    for folder in sorted(path for path in image_root.iterdir() if path.is_dir()):
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in preflight_batch.IMAGE_EXTENSIONS:
                mapped.setdefault(path.name, []).append(path)
    return mapped


def pending_rows_from_report(config: dict, report: preflight_batch.PreflightReport) -> list[dict[str, str]]:
    images_path = required_path(config, "images_csv")
    rows = read_csv(images_path)
    pending_names = set(report.pending_images)
    pending = [row for row in rows if row.get("Filename", "") in pending_names]
    discovered = source_image_paths(required_path(config, "image_root", directory=True))

    missing_or_ambiguous = [
        row.get("Filename", "")
        for row in pending
        if len(discovered.get(row.get("Filename", ""), [])) != 1
    ]
    if missing_or_ambiguous:
        raise SystemExit(
            "Pending image list contains missing or ambiguous source file(s): "
            + ", ".join(missing_or_ambiguous)
        )
    return pending


def ensure_configured_output_root(config: dict) -> Path:
    raw = str(config.get("crop_output", "")).strip()
    if not raw:
        raise SystemExit("Missing configured path: crop_output")
    root = Path(raw)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"Could not create configured crop_output: {root}: {exc}") from exc
    if not root.is_dir():
        raise SystemExit(f"Configured crop_output is not a directory: {root}")

    try:
        with tempfile.TemporaryDirectory(prefix=".workflow-write-test-", dir=root) as probe_dir:
            Path(probe_dir, "probe.txt").write_text("ok\n", encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Crop output folder is not writable: {root}: {exc}") from exc
    return root


def macro_path(value: str | Path) -> str:
    return str(Path(value)).replace("\\", "/").replace('"', '\\"')


def replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected one source setting, found {count}: {old}")
    return source.replace(old, new, 1)


def configure_source_settings(source: str, config: dict) -> str:
    replacements = {
        'gridFile   = "path here";': f'gridFile   = "{macro_path(config["grid_csv"])}";',
        'imagesFile = "path here";': f'imagesFile = "{macro_path(PENDING_IMAGES_CSV)}";',
        'stateFile  = "path here";': f'stateFile  = "{macro_path(LEGACY_STATE_FILE)}";',
        'inputRoot  = "path here";': f'inputRoot  = "{macro_path(config["image_root"])}";',
        'outputRoot = "path here";': f'outputRoot = "{macro_path(config["crop_output"])}";',
        "CROP_W = 130;": f'CROP_W = {config["crop_width"]};',
        "CROP_H = 546;": f'CROP_H = {config["crop_height"]};',
    }
    for old, new in replacements.items():
        source = replace_once(source, old, new)
    return source


def build_legacy_macro(config: dict) -> Path:
    source = configure_source_settings(SOURCE_MACRO.read_text(encoding="utf-8"), config)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_LEGACY_MACRO.write_text(source, encoding="utf-8")
    return CONFIGURED_LEGACY_MACRO


def build_macro(config: dict) -> Path:
    source = configure_source_settings(SOURCE_MACRO.read_text(encoding="utf-8"), config)

    # The production source macro's original four-point route only understood
    # 10/12-column layouts. Full-column geometry is generic for any validated
    # GridCols >= 2, so neutralize only that legacy source guard here. The
    # preserved fallback continues to use the original guard unchanged.
    source = replace_once(
        source,
        "        if (gridCols != 10 && gridCols != 12) {",
        "        if (gridCols < 2) {",
    )

    if source.count(START_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise SystemExit("Production macro calibration markers changed; refusing to guess where to patch.")

    start = source.index(START_MARKER)
    end = source.index(END_MARKER, start) + len(END_MARKER)

    full_column = FULL_COLUMN_MACRO.read_text(encoding="utf-8")
    composed = f'''        // ====================================================
        // FULL-COLUMN COMPOSED ROUTE
        // Existing folder/CSV lookup above and close/logging below are preserved.
        // ====================================================

{full_column}
'''
    source = source[:start] + composed + source[end:]
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_MACRO.write_text(source, encoding="utf-8")
    return CONFIGURED_MACRO


def launch_fiji(config: dict, macro: Path) -> int:
    fiji = required_path(config, "fiji_executable")
    return subprocess.call([str(fiji), "-macro", str(macro)])


def run_preflight(config: dict) -> preflight_batch.PreflightReport:
    csv_problems = validate_csvs(
        required_path(config, "grid_csv"),
        required_path(config, "images_csv"),
        required_path(config, "condition_order_csv"),
    )
    if csv_problems:
        raise SystemExit("CSV validation failed:\n- " + "\n- ".join(csv_problems))

    report = preflight_batch.preflight(config)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    PREFLIGHT_REPORT.write_text(report.render(), encoding="utf-8")
    if report.blocking_problems:
        raise SystemExit(report.render())
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", action="store_true", help="Use preserved four-point alignment route")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare pending metadata/configured macro without launching Fiji")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    report = run_preflight(config)
    ensure_configured_output_root(config)
    pending = pending_rows_from_report(config, report)
    write_pending_images(pending, PENDING_IMAGES_CSV)

    macro = build_legacy_macro(config) if args.legacy else build_macro(config)
    label = "four-point fallback" if args.legacy else "composed batch"
    print(f"Prepared {label} for {len(pending)} pending image(s): {macro}")

    if args.prepare_only:
        return 0
    return launch_fiji(config, macro)


if __name__ == "__main__":
    raise SystemExit(main())
