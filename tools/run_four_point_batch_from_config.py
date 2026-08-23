from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

try:
    from tools import crop_replacement_manifest, preflight_batch
except ModuleNotFoundError:
    import crop_replacement_manifest
    import preflight_batch

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MACRO = REPO_ROOT / "existing scripts clean" / "roibox RUN ALL IN PARENT.ijm"
VALIDATOR = REPO_ROOT / "tools" / "validate_project_csvs.py"
PREFLIGHT = REPO_ROOT / "tools" / "preflight_batch.py"
PREFLIGHT_REPORT = APP_DIR / "last_preflight.txt"
# Generated Fiji handoff. Its first two fields are the exact source identity.
PENDING_IMAGES_TSV = APP_DIR / "pending_images.tsv"
CONFIGURED_FOUR_POINT_MACRO = APP_DIR / "four_point_batch.configured.ijm"
FOUR_POINT_STATE_FILE = APP_DIR / "four_point_run.state.txt"
REPLACEMENT_MANIFEST = APP_DIR / "four_point_batch_replacement_manifest.tsv"
CONTROL_REQUEST_FILE = APP_DIR / "four_point_control.request"
RESUME_MARKER_FILE = APP_DIR / "four_point_resume.marker"
ACTIVE_BATCH_FILE = APP_DIR / "four_point_batch.active"
OWNED_FIJI_PIDS_FILE = APP_DIR / "four_point_owned_fiji_pids.txt"

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
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid crop dimension: {exc}") from exc
    if data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Crop dimensions must be positive.")
    return data


def validate_runtime_files(config: dict, require_fiji: bool) -> None:
    required_files = [SOURCE_MACRO, VALIDATOR, PREFLIGHT]
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


def validate_four_point_grid_widths(config: dict) -> None:
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


def run_preflight(*, allow_empty: bool = False) -> int:
    require_fiji_handoff_paths = False

    args = [
        sys.executable,
        str(PREFLIGHT),
        "--report",
        str(PREFLIGHT_REPORT),
        "--pending-images-csv",
        str(PENDING_IMAGES_TSV.with_suffix(".csv")),
    ]
    if not require_fiji_handoff_paths:
        args.append("--no-fiji-handoff-path-rules")
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise SystemExit(output or f"Batch preflight failed. See {PREFLIGHT_REPORT}")

    with PENDING_IMAGES_TSV.with_suffix(".csv").open("r", encoding="utf-8-sig", newline="") as handle:
        pending = sum(1 for _ in csv.DictReader(handle))
    if pending == 0 and not allow_empty:
        raise SystemExit(f"All expected crops already exist. See {PREFLIGHT_REPORT}")
    return pending


def restrict_pending_to_subfolder(config: dict, subfolder: str | None, *, include_completed: bool = False) -> list[dict[str, str]]:
    """Write an exact folder + filename handoff, optionally including completed plates."""
    run_preflight(allow_empty=include_completed)
    pending_csv = PENDING_IMAGES_TSV.with_suffix(".csv")
    with pending_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    sources = preflight_batch.discover_sources(Path(config["image_root"]))
    source_by_name = {path.name.casefold(): path for path in sources}

    if include_completed:
        with Path(config["images_csv"]).open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if (row.get("Filename") or "").casefold() in source_by_name
            ]
    if subfolder:
        wanted = subfolder.casefold()
        source_names = {
            path.name.casefold() for path in sources
            if path.parent.name.casefold() == wanted
        }
        if not source_names:
            raise SystemExit(f"No image subfolder named {subfolder!r} exists directly under image_root.")
        rows = [row for row in rows if (row.get("Filename") or "").casefold() in source_names]
    if not rows:
        raise SystemExit("No eligible images match the selected subfolder." if subfolder else "No eligible images remain.")

    scoped_rows: list[dict[str, str]] = []
    for row in rows:
        source = source_by_name.get((row.get("Filename") or "").casefold())
        if source is None:
            raise SystemExit(f"Selected pending image is not under image_root: {row.get('Filename', '')}")
        values = [source.parent.name, row.get("Filename", ""), row.get("Experiment", ""), row.get("Set", ""), row.get("Type", "")]
        if any("\t" in value or "\r" in value or "\n" in value for value in values):
            raise SystemExit("Folder and image metadata used for Fiji batch handoff may not contain tabs or line breaks.")
        scoped_rows.append(
            {"Folder": values[0], "Filename": values[1], "Experiment": values[2], "Set": values[3], "Type": values[4]}
        )

    with PENDING_IMAGES_TSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Folder", "Filename", "Experiment", "Set", "Type"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(scoped_rows)
    return scoped_rows
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


def configure_source_settings(source: str, config: dict, replacement_manifest: Path | None = None, state_file: Path | None = None) -> str:
    batch_qc = str(config.get("batch_grid_qc", "1")).casefold() not in {"0", "false", "no", "off"}
    hide_source = str(config.get("hide_source_during_alignment", "1")).casefold() not in {"0", "false", "no", "off"}
    source = replace_once(
        source,
        'replacementManifest = "path here";',
        'replacementManifest = "path here";' + "\n" + 'controlFile = "path here";',
    )
    replacements = {
        'gridFile   = "path here";': f'gridFile   = "{macro_path(config["grid_csv"])}";',
        'imagesFile = "path here";': f'imagesFile = "{macro_path(PENDING_IMAGES_TSV)}";',
        'stateFile  = "path here";': f'stateFile  = "{macro_path(state_file or FOUR_POINT_STATE_FILE)}";',
        'replacementManifest = "path here";': f'replacementManifest = "{macro_path(replacement_manifest)}";' if replacement_manifest else 'replacementManifest = "";',
        'controlFile = "path here";': f'controlFile = "{macro_path(CONTROL_REQUEST_FILE)}";',
        'inputRoot  = "path here";': f'batchGridQC = {1 if batch_qc else 0};\nhideSourceDuringAlignment = {1 if hide_source else 0};\nresumeBatch = File.exists("{macro_path(RESUME_MARKER_FILE)}");\ninputRoot  = "{macro_path(config["image_root"])}";',
        'outputRoot = "path here";': f'outputRoot = "{macro_path(config["crop_output"])}";',
        "CROP_W = 130;": f'CROP_W = {config["crop_width"]};',
        "CROP_H = 546;": f'CROP_H = {config["crop_height"]};',
    }
    for old, new in replacements.items():
        source = replace_once(source, old, new)
    return source

def enhance_metadata_lookup(source: str) -> str:
    """Bind batch metadata to folder + filename, never just a basename."""
    start_marker = "        // LOOK UP IMAGE IN images.csv BEFORE OPENING IT"
    end_marker = "        // In controller use, absence normally means this source is already"
    start = source.find(start_marker)
    end = source.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit("Legacy metadata lookup markers changed; refusing to generate an unsafe batch macro.")
    lookup = '''        // LOOK UP THIS EXACT SOURCE IN THE GENERATED TSV HANDOFF.
        experiment = "";
        setName = "";
        typeName = "";
        sourcePrefix = toLowerCase(cleanFolderName + "\\t" + fileName + "\\t");
        for (i = 1; i < imgLines.length; i++) {
            line = replace(imgLines[i], "\\r", "");
            if (!startsWith(toLowerCase(line), sourcePrefix))
                continue;
            metadata = split(substring(line, lengthOf(sourcePrefix)), "\\t");
            experiment = clean(metadata[0]);
            setName = clean(metadata[1]);
            typeName = clean(metadata[2]);
            break;
        }
        stateKey = cleanFolderName + "/" + fileName;
        if (resumeBatch && recordedRun(stateKey) > 0) {
            print("RESUME SKIP - already exported this batch: " + stateKey);
            continue;
        }

'''
    return source[:start] + lookup + source[end:]

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

        // Disposable alignment-only copy. Source pixels remain untouched.
        selectWindow(sourceTitle);
        if (isOpen("__alignment_view__")) {
            selectWindow("__alignment_view__");
            close();
            selectWindow(sourceTitle);
        }
        run("Duplicate...", "title=__alignment_view__");

        getDimensions(viewW, viewH, viewC, viewZ, viewT);
        run("Select None");
        roiBoxW = parseFloat(call("ij.Prefs.get", "rect.width", 108));
        roiBoxH = parseFloat(call("ij.Prefs.get", "rect.height", 108));
        roiBoxSize = maxOf(roiBoxW, roiBoxH);
        claheBlock = maxOf(400, round(roiBoxSize * 4));
        claheOptions = "blocksize=" + claheBlock + " histogram=256 maximum=1000 mask=*None* fast_(less_accurate)";
        run("Enhance Local Contrast (CLAHE)", claheOptions);
        run("Enhance Local Contrast (CLAHE)", claheOptions);

        roiToolsetPath = getDirectory("macros") + "toolsets/Roi 1-Click Tools.ijm";
        if (File.exists(roiToolsetPath))
            run("Install...", "install=[" + roiToolsetPath + "]");

        roiClickToolFound = 0;
        for (toolCandidate = 15; toolCandidate <= 21; toolCandidate++) {
            setTool(toolCandidate);
            if (startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")) {
                roiClickToolFound = 1;
                break;
            }
        }
        if (roiClickToolFound == 0)
            showMessage("ROI 1-click", "The Rotated Rectangle Click Tool could not be selected automatically. The Fiji toolbar is visible so you can select it manually, then continue.");

        QC_W = roiBoxW;
        QC_H = roiBoxH;
        accepted = 0;

        // Brief yield: let Java AWT finish painting the main ImageJ toolbar and
        // plate image before the first modal waitForUser dialog appears.
        // This is needed on cold launch because -macro runs on the main thread
        // before the Event Dispatch Thread has processed all pending paint events.
        wait(300);

        while (accepted == 0) {
            Overlay.remove;

            waitForUser(
                "1 / 4 -- R1C1 -- " + sourceTitle + " -- Z=OK, C=CANCEL",
                "Target: Row 1, Column 1 [+] Centre ROI box around target at R1C1, then click OK. [+] Exp: " + experiment + ", Set: " + setName + " [+] Grid: 8R x " + gridCols + "C [+] Export count: " + (nWanted * 2)
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for R1C1.");
            R1LX = x + w / 2;
            R1LY = y + h / 2;

            waitForUser(
                "2 / 4 -- R1C" + gridCols + " -- " + sourceTitle + " -- Z=OK, C=CANCEL",
                "Target: Row 1, Column " + gridCols + " [+] Centre ROI box around target at R1C" + gridCols + ", then click OK. [+] Exp: " + experiment + ", Set: " + setName + " [+] Grid: 8R x " + gridCols + "C [+] Export count: " + (nWanted * 2)
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for row 1 right.");
            R1RX = x + w / 2;
            R1RY = y + h / 2;

            waitForUser(
                "3 / 4 -- R5C1 -- " + sourceTitle + " -- Z=OK, C=CANCEL",
                "Target: Row 5, Column 1 [+] Centre ROI box around target at R5C1, then click OK. [+] Exp: " + experiment + ", Set: " + setName + " [+] Grid: 8R x " + gridCols + "C [+] Export count: " + (nWanted * 2)
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for R5C1.");
            R5LX = x + w / 2;
            R5LY = y + h / 2;

            waitForUser(
                "4 / 4 -- R5C" + gridCols + " -- " + sourceTitle + " -- Z=OK, C=CANCEL",
                "Target: Row 5, Column " + gridCols + " [+] Centre ROI box around target at R5C" + gridCols + ", then click OK. [+] Exp: " + experiment + ", Set: " + setName + " [+] Grid: 8R x " + gridCols + "C [+] Export count: " + (nWanted * 2)
            );
            getSelectionBounds(x, y, w, h);
            if (w <= 0 || h <= 0)
                exit("No rectangle ROI found for row 5 right.");
            R5RX = x + w / 2;
            R5RY = y + h / 2;

            // Pure mathematical 8 x N lattice from the four authoritative centres.
            gridHX = ((R1RX - R1LX) + (R5RX - R5LX)) / 2;
            gridHY = ((R1RY - R1LY) + (R5RY - R5LY)) / 2;
            gridVX = ((R5LX - R1LX) + (R5RX - R1RX)) / 2;
            gridVY = ((R5LY - R1LY) + (R5RY - R1RY)) / 2;
            hLen = sqrt(gridHX * gridHX + gridHY * gridHY);
            vLen = sqrt(gridVX * gridVX + gridVY * gridVY);
            if (hLen <= 0 || vLen <= 0)
                exit("Four-point geometry collapsed to a zero-length grid axis.");
            hux = gridHX / hLen;
            huy = gridHY / hLen;
            vux = gridVX / vLen;
            vuy = gridVY / vLen;
            Overlay.remove;
            setColor("cyan");
            for (qcRow = 1; qcRow <= 8; qcRow++) {
                v = (qcRow - 1) / 4;
                qcLeftX = R1LX + v * (R5LX - R1LX);
                qcLeftY = R1LY + v * (R5LY - R1LY);
                qcRightX = R1RX + v * (R5RX - R1RX);
                qcRightY = R1RY + v * (R5RY - R1RY);
                Overlay.drawLine(qcLeftX, qcLeftY, qcRightX, qcRightY);
                for (qcCol = 1; qcCol <= gridCols; qcCol++) {
                    u = (qcCol - 1) / (gridCols - 1);
                    qcX = qcLeftX + u * (qcRightX - qcLeftX);
                    qcY = qcLeftY + u * (qcRightY - qcLeftY);
                    p1x = qcX - (QC_W / 2) * hux - (QC_H / 2) * vux;
                    p1y = qcY - (QC_W / 2) * huy - (QC_H / 2) * vuy;
                    p2x = qcX + (QC_W / 2) * hux - (QC_H / 2) * vux;
                    p2y = qcY + (QC_W / 2) * huy - (QC_H / 2) * vuy;
                    p3x = qcX + (QC_W / 2) * hux + (QC_H / 2) * vux;
                    p3y = qcY + (QC_W / 2) * huy + (QC_H / 2) * vuy;
                    p4x = qcX - (QC_W / 2) * hux + (QC_H / 2) * vux;
                    p4y = qcY - (QC_W / 2) * huy + (QC_H / 2) * vuy;
                    Overlay.drawLine(p1x, p1y, p2x, p2y);
                    Overlay.drawLine(p2x, p2y, p3x, p3y);
                    Overlay.drawLine(p3x, p3y, p4x, p4y);
                    Overlay.drawLine(p4x, p4y, p1x, p1y);
                }
            }
            for (qcCol = 1; qcCol <= gridCols; qcCol++) {
                u = (qcCol - 1) / (gridCols - 1);
                topX = R1LX + u * (R1RX - R1LX);
                topY = R1LY + u * (R1RY - R1LY);
                bottomLeftX = R1LX + 1.75 * (R5LX - R1LX);
                bottomLeftY = R1LY + 1.75 * (R5LY - R1LY);
                bottomRightX = R1RX + 1.75 * (R5RX - R1RX);
                bottomRightY = R1RY + 1.75 * (R5RY - R1RY);
                bottomX = bottomLeftX + u * (bottomRightX - bottomLeftX);
                bottomY = bottomLeftY + u * (bottomRightY - bottomLeftY);
                Overlay.drawLine(topX, topY, bottomX, bottomY);
            }
            Overlay.show;

            // GenericDialog only places a choice beside its own label. Keep the
            // entire instruction on that single compact row rather than adding
            // a vertically separate message row.
            if (batchGridQC) {
                Dialog.create("Full-grid QC -- Inspect 8R x " + gridCols + "C grid -- Z=ACCEPT, X=RETRY, C=CANCEL");
                Dialog.addChoice(
                    "ACCEPT: Export crops. [+] RETRY: Repeat four-point calibration.",
                    newArray("ACCEPT", "RETRY"),
                    "ACCEPT"
                );
                Dialog.show();
                qcAction = Dialog.getChoice();
                if (qcAction == "ACCEPT")
                    accepted = 1;
                else
                    Overlay.remove;
            } else {
                accepted = 1;
            }
        }

        Overlay.remove;
        close();
        selectWindow(sourceTitle);
        // Validate every planned rectangle before replacement archiving or the
        // first output write. A bad calibration therefore leaves prior crops
        // and the source image untouched.
        getDimensions(sourceW, sourceH, sourceC, sourceZ, sourceT);
        boundsTopFactor = 0.375;
        boundsLowFactor = 1.375;
        for (boundsI = 0; boundsI < nWanted; boundsI++) {
            boundsCol = columns[boundsI];
            boundsU = (boundsCol - 1) / (gridCols - 1);

            boundsLeftX = R1LX + boundsTopFactor * (R5LX - R1LX);
            boundsLeftY = R1LY + boundsTopFactor * (R5LY - R1LY);
            boundsRightX = R1RX + boundsTopFactor * (R5RX - R1RX);
            boundsRightY = R1RY + boundsTopFactor * (R5RY - R1RY);
            boundsCX = boundsLeftX + boundsU * (boundsRightX - boundsLeftX);
            boundsCY = boundsLeftY + boundsU * (boundsRightY - boundsLeftY);
            requireCropFits(
                boundsCX, boundsCY, CROP_W, CROP_H,
                sourceW, sourceH, sourceTitle, boundsCol, "Top"
            );

            boundsLeftX = R1LX + boundsLowFactor * (R5LX - R1LX);
            boundsLeftY = R1LY + boundsLowFactor * (R5LY - R1LY);
            boundsRightX = R1RX + boundsLowFactor * (R5RX - R1RX);
            boundsRightY = R1RY + boundsLowFactor * (R5RY - R1RY);
            boundsCX = boundsLeftX + boundsU * (boundsRightX - boundsLeftX);
            boundsCY = boundsLeftY + boundsU * (boundsRightY - boundsLeftY);
            requireCropFits(
                boundsCX, boundsCY, CROP_W, CROP_H,
                sourceW, sourceH, sourceTitle, boundsCol, "Low"
            );
        }

        archiveReplacementCrops(cleanFolderName, fileName);

'''
    completion_marker = '''showMessage(
    "ALL DONE",
    "Processed images: " + processedImages + "\\n" +
    "Not listed / not pending: " + notListedImages + "\\n" +
    "Skipped after metadata match: " + skippedImages + "\\n\\n" +
    "Outputs saved under:\\n" +
    outputRoot
);
'''
    if completion_marker not in source:
        raise SystemExit("Legacy completion dialog changed; refusing to guess where to release the batch wrapper.")
    source = source.replace(completion_marker, completion_marker + 'File.saveString("complete\\n", controlFile);\n', 1)
    return source[:start] + block + source[export:]


def build_four_point_macro(config: dict, replacement_manifest: Path | None = None, state_file: Path | None = None) -> Path:
    source = configure_source_settings(SOURCE_MACRO.read_text(encoding="utf-8"), config, replacement_manifest, state_file)
    source = enhance_metadata_lookup(source)
    source = enhance_four_point_macro(source)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_FOUR_POINT_MACRO.write_text(source, encoding="utf-8")
    return CONFIGURED_FOUR_POINT_MACRO


def remember_owned_fiji_process(pid: int) -> None:
    OWNED_FIJI_PIDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OWNED_FIJI_PIDS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"{pid}\n")

def control_request() -> str:
    try:
        return CONTROL_REQUEST_FILE.read_text(encoding="utf-8").strip().casefold()
    except FileNotFoundError:
        return ""


def kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)


def run_fiji_batch(fiji: Path, macro: Path, session_state: Path) -> None:
    """Supervise only the Fiji process tree launched for this batch."""
    ACTIVE_BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_BATCH_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    # These are runtime-only files created for this batch; historical state is
    # never touched. They are removed on completion, cancellation, or error.
    for path in (CONTROL_REQUEST_FILE, RESUME_MARKER_FILE):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        while True:
            process = subprocess.Popen([str(fiji), "--no-splash", "-macro", str(macro)])
            remember_owned_fiji_process(process.pid)
            restart = False
            while process.poll() is None:
                request = control_request()
                if request in {"cancel", "restart", "complete"}:
                    if request == "complete":
                        return
                    if request == "restart":
                        RESUME_MARKER_FILE.write_text("resume\n", encoding="utf-8")
                        restart = True
                    kill_process_tree(process)
                    break
                time.sleep(0.1)
            process.wait()
            # Escape can close Fiji before the polling loop observes X. Read the
            # persisted request once more before deciding whether to restart.
            final_request = control_request()
            if final_request == "restart" or restart:
                RESUME_MARKER_FILE.write_text("resume\n", encoding="utf-8")
                try:
                    CONTROL_REQUEST_FILE.unlink()
                except FileNotFoundError:
                    pass
                continue
            if final_request == "complete":
                return
            if final_request == "cancel":
                return
            returncode = process.returncode
            if returncode != 0:
                raise SystemExit(f"Fiji exited with code {returncode} before four-point completion; crops may be incomplete.")
            raise SystemExit(
                "Fiji launcher exited before the four-point completion sentinel; no success was recorded. "
                "This can indicate unsupported existing-instance forwarding or an interrupted macro."
            )
    finally:
        for path in (CONTROL_REQUEST_FILE, RESUME_MARKER_FILE, ACTIVE_BATCH_FILE, session_state):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="validate/preflight and build the configured Fiji macro without requiring or launching Fiji",
    )
    parser.add_argument("--subfolder", help="process only this immediate image-root subfolder")
    parser.add_argument("--replace-existing-crops", action="store_true", help="archive existing crops after accepted grid QC, then export replacements")
    args = parser.parse_args()

    config = load_config(
        require_fiji=not args.prepare_only,
        require_fiji_handoff_paths=False,
    )
    validate_runtime_files(config, require_fiji=not args.prepare_only)
    validate_csvs(config)
    validate_four_point_grid_widths(config)
    rows = restrict_pending_to_subfolder(config, args.subfolder, include_completed=args.replace_existing_crops)
    ensure_crop_output_root(config)
    replacement_manifest = None
    if args.replace_existing_crops:
        crop_replacement_manifest.write_manifests(config, rows, REPLACEMENT_MANIFEST)
        replacement_manifest = REPLACEMENT_MANIFEST
    session_state = APP_DIR / f"four_point_session_{uuid.uuid4().hex}.state.txt"
    macro = build_four_point_macro(config, replacement_manifest, session_state)

    if args.prepare_only:
        action = "replacement-ready" if args.replace_existing_crops else "pending"
        print(f"Prepared four-point batch for {len(rows)} {action} image(s): {macro}")
        return

    fiji = Path(config["fiji_executable"])
    run_fiji_batch(fiji, macro, session_state)



if __name__ == "__main__":
    main()
