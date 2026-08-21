from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import tempfile
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
CONFIGURED_LEGACY_MACRO = APP_DIR / "batch_four_point_fallback.configured.ijm"
LEGACY_STATE_FILE = APP_DIR / "four_point_fallback.state.txt"

START_MARKER = "        // ====================================================\n        // IDENTIFY CURRENT PLATE"
END_MARKER = "        setBatchMode(false);"
LEGACY_EXPORT_MARKER = "        // ====================================================\n        // EXPORT CROPS"


def load_config(
    require_fiji: bool = True,
    require_fiji_handoff_paths: bool = True,
) -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read config.json: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("config.json must contain a JSON object of named settings.")

    required = [
        "image_root",
        "crop_output",
        "grid_csv",
        "images_csv",
        "condition_order_csv",
    ]
    if require_fiji:
        required.insert(0, "fiji_executable")
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))

    if require_fiji_handoff_paths:
        for key in ("grid_csv", "crop_output"):
            if ";" in str(data[key]):
                raise SystemExit(
                    f"Configured {key} contains a semicolon, which conflicts with the composed Fiji macro-argument delimiter: {data[key]}"
                )

    try:
        data["alignment_tolerance"] = float(data.get("alignment_tolerance", 0.08))
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid processing setting: {exc}") from exc
    if not math.isfinite(data["alignment_tolerance"]):
        raise SystemExit("Alignment tolerance must be a finite number.")
    if data["alignment_tolerance"] <= 0 or data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Alignment tolerance and crop dimensions must be positive.")
    return data


def validate_runtime_files(config: dict, require_fiji: bool, legacy: bool = False) -> None:
    required_files = [SOURCE_MACRO, VALIDATOR, PREFLIGHT]
    if not legacy:
        required_files.extend([ALIGNMENT_MACRO, CROP_HELPER])
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        raise SystemExit("Required workflow file(s) missing:\n" + "\n".join(str(path) for path in missing))

    if require_fiji:
        fiji = Path(config.get("fiji_executable", ""))
        if not fiji.is_file():
            raise SystemExit(f"Fiji executable not found: {fiji}")


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


def validate_legacy_grid_widths(config: dict) -> None:
    path = Path(config["grid_csv"])
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    widths = sorted({int((row.get("GridCols") or "0").strip()) for row in rows})
    unsupported = [value for value in widths if value not in (10, 12)]
    if unsupported:
        raise SystemExit(
            "The preserved four-point fallback only supports its original 10- or 12-column grids. "
            "Unsupported GridCols: " + ", ".join(str(value) for value in unsupported)
        )


def run_preflight(
    legacy: bool = False,
    require_fiji_handoff_paths: bool | None = None,
) -> int:
    if require_fiji_handoff_paths is None:
        require_fiji_handoff_paths = not legacy

    args = [
        sys.executable,
        str(PREFLIGHT),
        "--report",
        str(PREFLIGHT_REPORT),
        "--pending-images-csv",
        str(PENDING_IMAGES_CSV),
    ]
    if not require_fiji_handoff_paths:
        args.append("--no-fiji-handoff-path-rules")
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise SystemExit(output or f"Batch preflight failed. See {PREFLIGHT_REPORT}")

    with PENDING_IMAGES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        pending = sum(1 for _ in csv.DictReader(handle))
    if pending == 0:
        raise SystemExit(f"All expected crops already exist. See {PREFLIGHT_REPORT}")
    return pending


def ensure_crop_output_root(config: dict) -> Path:
    root = Path(config["crop_output"])
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"Could not create crop output folder {root}: {exc}") from exc
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


def enhance_four_point_macro(source: str) -> str:
    """Keep the mature four-point math/export, replacing only its interaction block."""
    if source.count(START_MARKER) != 1 or source.count(LEGACY_EXPORT_MARKER) != 1:
        raise SystemExit("Four-point calibration markers changed; refusing to guess where to patch.")

    start = source.index(START_MARKER)
    export = source.index(LEGACY_EXPORT_MARKER, start)
    block = r'''        // ====================================================
        // FOUR-POINT MATHEMATICAL ALIGNMENT + QC
        // Geometry remains the established R1C1/R1C(last)/R5C1/R5C(last)
        // centre-click method. The boosted alignment view is a disposable copy;
        // source pixels and the established crop export remain untouched.
        // ====================================================

        showMessage(
            "Next plate",
            "Folder: " + cleanFolderName + "\n\n" +
            "Image: " + sourceTitle + "\n\n" +
            "Experiment: " + experiment + "\n" +
            "Set: " + setName + "\n" +
            "Type: " + typeName + "\n" +
            "Grid: 8 x " + gridCols + "\n" +
            "Exports: " + (nWanted * 2) + "\n\n" +
            "A temporary boosted alignment view will open. Centre the 108x108 box four times."
        );

        // Disposable alignment-only copy: sample the central 30% so bright
        // plate rims do not dominate the temporary contrast stretch.
        selectWindow(sourceTitle);
        if (isOpen("__alignment_view__")) {
            selectWindow("__alignment_view__");
            close();
            selectWindow(sourceTitle);
        }
        run("Duplicate...", "title=__alignment_view__");
        getDimensions(viewW, viewH, viewC, viewZ, viewT);
        sampleW = round(viewW * 0.30);
        sampleH = round(viewH * 0.30);
        sampleX = round((viewW - sampleW) / 2);
        sampleY = round((viewH - sampleH) / 2);
        makeRectangle(sampleX, sampleY, sampleW, sampleH);
        run("Enhance Contrast", "saturated=0.35");

        CLICK_ROI = 108;
        accepted = 0;
        makeRectangle(round(viewW / 2 - CLICK_ROI / 2), round(viewH / 2 - CLICK_ROI / 2), CLICK_ROI, CLICK_ROI);

        while (accepted == 0) {
            Overlay.remove;

            waitForUser(
                "1 / 4 — R1C1",
                sourceTitle + "\n\nCentre box on ROW 1, COLUMN 1.\n\nReposition as needed, then click OK."
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for R1C1.");
            R1LX = x + w / 2;
            R1LY = y + h / 2;

            waitForUser(
                "2 / 4 — R1C" + gridCols,
                sourceTitle + "\n\nCentre box on ROW 1, COLUMN " + gridCols + ".\n\nReposition as needed, then click OK."
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for row 1 right.");
            R1RX = x + w / 2;
            R1RY = y + h / 2;

            waitForUser(
                "3 / 4 — R5C1",
                sourceTitle + "\n\nCentre box on ROW 5, COLUMN 1.\n\nReposition as needed, then click OK."
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for R5C1.");
            R5LX = x + w / 2;
            R5LY = y + h / 2;

            waitForUser(
                "4 / 4 — R5C" + gridCols,
                sourceTitle + "\n\nCentre box on ROW 5, COLUMN " + gridCols + ".\n\nReposition as needed, then click OK."
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for row 5 right.");
            R5RX = x + w / 2;
            R5RY = y + h / 2;

            // Pure mathematical 8 x N lattice from the four authoritative centres.
            Overlay.remove;
            setColor("cyan");
            for (qcRow = 1; qcRow <= 8; qcRow++) {
                v = (qcRow - 1) / 4;
                qcLeftX = R1LX + v * (R5LX - R1LX);
                qcLeftY = R1LY + v * (R5LY - R1LY);
                qcRightX = R1RX + v * (R5RX - R1RX);
                qcRightY = R1RY + v * (R5RY - R1RY);
                for (qcCol = 1; qcCol <= gridCols; qcCol++) {
                    u = (qcCol - 1) / (gridCols - 1);
                    qcX = qcLeftX + u * (qcRightX - qcLeftX);
                    qcY = qcLeftY + u * (qcRightY - qcLeftY);
                    Overlay.drawRect(qcX - CLICK_ROI / 2, qcY - CLICK_ROI / 2, CLICK_ROI, CLICK_ROI);
                }
            }
            Overlay.show;

            Dialog.create("Full-grid QC");
            Dialog.addMessage(
                "Inspect the mathematically calculated 8 x " + gridCols + " grid.\n\n" +
                "Accept exports the fixed-size crops from the unchanged source image. Retry repeats the four centre placements."
            );
            Dialog.addChoice("Action", newArray("Accept", "Retry"), "Accept");
            Dialog.show();
            qcAction = Dialog.getChoice();
            if (qcAction == "Accept") {
                accepted = 1;
            } else {
                Overlay.remove;
                makeRectangle(round(R1LX - CLICK_ROI / 2), round(R1LY - CLICK_ROI / 2), CLICK_ROI, CLICK_ROI);
            }
        }

        Overlay.remove;
        close();
        selectWindow(sourceTitle);

'''
    return source[:start] + block + source[export:]


def build_legacy_macro(config: dict) -> Path:
    source = configure_source_settings(SOURCE_MACRO.read_text(encoding="utf-8"), config)
    source = enhance_four_point_macro(source)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_LEGACY_MACRO.write_text(source, encoding="utf-8")
    return CONFIGURED_LEGACY_MACRO


def build_macro(config: dict) -> Path:
    source = configure_source_settings(SOURCE_MACRO.read_text(encoding="utf-8"), config)

    source = replace_once(
        source,
        "        if (gridCols != 10 && gridCols != 12) {",
        "        if (gridCols < 2) {",
    )

    if source.count(START_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise SystemExit("Production macro calibration markers changed; refusing to guess where to patch.")

    start = source.index(START_MARKER)
    end = source.index(END_MARKER, start) + len(END_MARKER)

    composed = f'''        // ====================================================
        // FULL-COLUMN COMPOSED ROUTE
        // Existing folder/CSV lookup above and close/logging below are preserved.
        // Completed images were removed from the temporary metadata preflight.
        // ====================================================

        showStatus(
            cleanFolderName + " | " + sourceTitle + " | " +
            experiment + "/" + setName + "/" + typeName +
            " | grid 8x" + gridCols + " | exports " + (nWanted * 2)
        );

        alignmentResult = runMacro(
            "{macro_path(ALIGNMENT_MACRO)}",
            "cols=" + gridCols + ";rows=8;tolerance={config['alignment_tolerance']};" +
            "context=" + experiment + "/" + setName + "/" + typeName
        );
        if (alignmentResult != "accepted")
            exit("Full-column alignment did not complete successfully; crop export was not started.");

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
        help="validate/preflight and build the configured Fiji macro without requiring or launching Fiji",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="use the established four-point centre-click geometry with mathematical full-grid QC",
    )
    args = parser.parse_args()

    config = load_config(
        require_fiji=not args.prepare_only,
        require_fiji_handoff_paths=not args.legacy,
    )
    validate_runtime_files(config, require_fiji=not args.prepare_only, legacy=args.legacy)
    validate_csvs(config)
    if args.legacy:
        validate_legacy_grid_widths(config)
    pending = run_preflight(legacy=args.legacy)
    ensure_crop_output_root(config)
    macro = build_legacy_macro(config) if args.legacy else build_macro(config)

    if args.prepare_only:
        if args.legacy:
            print(f"Prepared four-point batch for {pending} pending image(s): {macro}")
        else:
            print(f"Prepared composed batch for {pending} pending image(s): {macro}")
        return

    fiji = Path(config["fiji_executable"])
    subprocess.Popen([str(fiji), "-macro", str(macro)])


if __name__ == "__main__":
    main()
