from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

try:
    from tools.preflight_batch import build_report as build_batch_report
except ModuleNotFoundError:
    from preflight_batch import build_report as build_batch_report

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
LAST_OUTPUT_FILE = APP_DIR / "last_pillow_output.txt"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "existing scripts clean"
VALIDATOR = REPO_ROOT / "tools" / "validate_project_csvs.py"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

SCRIPTS = {
    "matrices": "make_matrices.py",
    "all-strains": "allstrain matrix.py",
    "all-strains-dedup": "allstrainmatrix extra WT removed.py",
    "label-individual": "folder per strain all indiv strains labelled.py",
}


def validate_output_layout(crop_output: str | Path, matrix_output: str | Path) -> None:
    crop_root = Path(crop_output).resolve()
    matrix_root = Path(matrix_output).resolve()
    if matrix_root == crop_root or matrix_root.is_relative_to(crop_root):
        raise SystemExit(
            "Matrix output must be outside crop_output. The reused Pillow scripts search crop_output recursively, "
            "so putting generated matrices inside that tree would make later runs ingest their own outputs."
        )


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = ["crop_output", "matrix_output", "grid_csv", "images_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    validate_output_layout(data["crop_output"], data["matrix_output"])
    try:
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid crop dimensions: {exc}") from exc
    if data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Crop dimensions must be positive.")
    return data


def validate_csvs(config: dict) -> None:
    if not VALIDATOR.is_file():
        raise SystemExit(f"CSV validator not found: {VALIDATOR}")
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


def validate_source_readiness_if_configured(config: dict) -> None:
    if not str(config.get("image_root", "")).strip():
        return
    lines, problems, pending_rows = build_batch_report(config)
    if problems:
        raise SystemExit(
            "Source/crop preflight found blocking issues before Pillow output:\n" + "\n".join(lines)
        )
    if pending_rows:
        raise SystemExit(
            f"Source/crop preflight shows {len(pending_rows)} plate(s) still needing crop generation/rebuild. "
            "Run/finish the Fiji crop batch before producing final Pillow outputs.\n\n" + "\n".join(lines)
        )


def configured_copy(alias: str, config: dict) -> Path:
    source_path = SCRIPT_DIR / SCRIPTS[alias]
    source = source_path.read_text(encoding="utf-8")

    replacements = {
        'IMAGE_ROOT = Path(r"path here")': f"IMAGE_ROOT = Path({str(Path(config['crop_output']))!r})",
        'GRID_CSV = Path(r"path here")': f"GRID_CSV = Path({str(Path(config['grid_csv']))!r})",
        'IMAGES_CSV = Path(r"path here")': f"IMAGES_CSV = Path({str(Path(config['images_csv']))!r})",
        'CONDITION_ORDER_CSV = Path(r"path here")': f"CONDITION_ORDER_CSV = Path({str(Path(config['condition_order_csv']))!r})",
        'MATRIX_ROOT = Path(r"path here")': f"MATRIX_ROOT = Path({str(Path(config['matrix_output']))!r})",
    }

    for old, new in replacements.items():
        if source.count(old) != 1:
            raise SystemExit(f"{source_path.name}: expected one setting line, found {source.count(old)}: {old}")
        source = source.replace(old, new, 1)

    legacy_true = "ROTATE_IMAGES_90_CCW = True"
    legacy_false = "ROTATE_IMAGES_90_CCW = False"
    if source.count(legacy_true) == 1:
        source = source.replace(legacy_true, legacy_false, 1)
    elif source.count(legacy_false) != 1:
        raise SystemExit(f"{source_path.name}: expected one legacy rotation setting")

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out = APP_DIR / f"{source_path.stem}.configured.py"
    out.write_text(source, encoding="utf-8")
    return out


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def safe_name(value: str) -> str:
    replacements = {
        "/": "-",
        "\\": "-",
        ":": "-",
        "*": "-",
        "?": "",
        '"': "",
        "<": "(",
        ">": ")",
        "|": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def expected_crop_contract(grid_path: Path, images_path: Path) -> dict[str, str]:
    grid = read_csv_rows(grid_path)
    images = read_csv_rows(images_path)
    columns_by_grid: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    for row in grid:
        try:
            column = int(row.get("Column", ""))
        except ValueError as exc:
            raise SystemExit(f"Invalid grid column in {grid_path}: {row.get('Column', '')!r}") from exc
        columns_by_grid[(row.get("Experiment", ""), row.get("Set", ""))][column] = row.get("Strain", "")

    contract: dict[str, str] = {}
    for row in images:
        exp = row.get("Experiment", "")
        set_name = row.get("Set", "")
        type_name = row.get("Type", "")
        for column, strain in columns_by_grid.get((exp, set_name), {}).items():
            for state in ("Top", "Low"):
                prefix = f"{exp}_{set_name}_{type_name}_{column:02d}_{state}_".lower()
                exact_name = f"{exp}_{set_name}_{type_name}_{column:02d}_{state}_{safe_name(strain)}.png"
                contract[prefix] = exact_name
    return contract


def expected_crop_prefixes(grid_path: Path, images_path: Path) -> set[str]:
    return set(expected_crop_contract(grid_path, images_path))


def validate_unique_crop_matches(
    root: Path,
    grid_path: Path,
    images_path: Path,
    allow_missing: bool = False,
) -> list[Path]:
    if not root.is_dir():
        raise SystemExit(f"Crop output folder not found: {root}")

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    contract = expected_crop_contract(grid_path, images_path)
    ambiguous: list[tuple[str, list[Path]]] = []
    stale_mismatch: list[tuple[str, str, Path]] = []
    missing: list[str] = []
    selected: list[Path] = []

    for prefix, exact_name in sorted(contract.items()):
        matches = [path for path in files if path.stem.lower().startswith(prefix)]
        if len(matches) > 1:
            ambiguous.append((prefix, matches))
        elif len(matches) == 1:
            match = matches[0]
            if match.name.lower() != exact_name.lower():
                stale_mismatch.append((prefix, exact_name, match))
            else:
                selected.append(match)
        else:
            missing.append(prefix)

    if ambiguous:
        lines = [
            "Ambiguous crop inputs: the reused Pillow scripts would choose the first matching file.",
            "Remove/archive stale duplicates or correct metadata before generating outputs.",
        ]
        for prefix, matches in ambiguous[:20]:
            lines.append(f"{prefix}")
            lines.extend(f"  - {path.relative_to(root)}" for path in matches)
        if len(ambiguous) > 20:
            lines.append(f"... plus {len(ambiguous) - 20} more ambiguous logical cells")
        raise SystemExit("\n".join(lines))

    if stale_mismatch:
        lines = [
            "Stale crop filename mismatch: a legacy prefix match exists, but it is not the exact filename the current exporter/metadata require.",
            "The reused Pillow scripts would otherwise accept the stale file by prefix, so remove/archive it or rerun crop generation.",
        ]
        for prefix, expected, match in stale_mismatch[:20]:
            lines.append(f"{prefix}*")
            lines.append(f"  expected: {expected}")
            lines.append(f"  found:    {match.relative_to(root)}")
        if len(stale_mismatch) > 20:
            lines.append(f"... plus {len(stale_mismatch) - 20} more stale filename mismatches")
        raise SystemExit("\n".join(lines))

    if missing and not allow_missing:
        lines = [
            f"Incomplete crop inputs: {len(missing)} expected logical crop(s) are missing.",
            "Complete/rerun crop generation before producing final Pillow outputs.",
            "For an intentionally partial output, run this wrapper manually with --allow-missing.",
        ]
        lines.extend(f"  - {prefix}*" for prefix in missing[:20])
        if len(missing) > 20:
            lines.append(f"... plus {len(missing) - 20} more missing logical crops")
        raise SystemExit("\n".join(lines))

    if missing:
        print(f"Allowing intentional partial Pillow output with {len(missing)} missing logical crop(s).")

    return sorted(set(selected))


def normalize_crop_orientation(
    root: Path,
    crop_width: int,
    crop_height: int,
    paths: list[Path] | None = None,
    strict: bool = False,
) -> tuple[int, int, int]:
    if not root.is_dir():
        raise SystemExit(f"Crop output folder not found: {root}")
    if crop_width == crop_height:
        raise SystemExit("Automatic crop-orientation normalization requires non-square crop dimensions.")

    unrotated = (crop_width, crop_height)
    rotated_size = (crop_height, crop_width)
    rotated = 0
    already_ready = 0
    unexpected_paths: list[Path] = []

    candidates = paths if paths is not None else sorted(root.rglob("*.png"))
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with Image.open(path) as image:
                size = image.size
                if size == unrotated:
                    turned = image.transpose(Image.Transpose.ROTATE_90)
                    if path.suffix.lower() in {".jpg", ".jpeg"}:
                        if turned.mode not in ("RGB", "L"):
                            turned = turned.convert("RGB")
                        turned.save(path, quality=95)
                    else:
                        turned.save(path)
                    rotated += 1
                elif size == rotated_size:
                    already_ready += 1
                else:
                    unexpected_paths.append(path)
        except OSError as exc:
            raise SystemExit(f"Could not inspect/rotate crop {path}: {exc}") from exc

    if strict and unexpected_paths:
        details = "\n".join(
            f"  - {path.relative_to(root)}" for path in unexpected_paths[:20]
        )
        if len(unexpected_paths) > 20:
            details += f"\n  ... plus {len(unexpected_paths) - 20} more"
        raise SystemExit(
            "Current crop inputs have dimensions that match neither the configured crop size "
            f"{unrotated} nor its rotated size {rotated_size}:\n{details}"
        )

    print(
        "Crop orientation: "
        f"rotated {rotated}, already ready {already_ready}, unexpected-size inputs {len(unexpected_paths)}"
    )
    return rotated, already_ready, len(unexpected_paths)


def child_directories(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {path.resolve() for path in root.iterdir() if path.is_dir()}


def newest_new_directory(before: set[Path], after: set[Path]) -> Path | None:
    created = [path for path in after - before if path.is_dir()]
    if not created:
        return None
    return max(created, key=lambda path: path.stat().st_mtime_ns)


def cleanup_empty_new_directories(before: set[Path], after: set[Path]) -> tuple[list[Path], list[Path]]:
    removed: list[Path] = []
    retained: list[Path] = []
    for path in sorted(after - before):
        if not path.is_dir():
            continue
        try:
            if not any(path.iterdir()):
                path.rmdir()
                removed.append(path)
            else:
                retained.append(path)
        except OSError:
            retained.append(path)
    return removed, retained


def record_output(path: Path) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LAST_OUTPUT_FILE.write_text(str(path) + "\n", encoding="utf-8")


def open_output(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        print(f"Output folder: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", choices=sorted(SCRIPTS))
    parser.add_argument("--no-open-output", action="store_true")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="allow intentionally partial Pillow outputs instead of requiring every metadata-defined crop",
    )
    args = parser.parse_args()

    config = load_config()
    validate_csvs(config)
    configured = configured_copy(args.script, config)

    crop_root = Path(config["crop_output"])
    selected_crops = validate_unique_crop_matches(
        crop_root,
        Path(config["grid_csv"]),
        Path(config["images_csv"]),
        allow_missing=args.allow_missing,
    )
    validate_source_readiness_if_configured(config)
    normalize_crop_orientation(
        crop_root,
        config["crop_width"],
        config["crop_height"],
        paths=selected_crops,
        strict=True,
    )

    output_root = Path(config["matrix_output"])
    before = child_directories(output_root)
    result = subprocess.run([sys.executable, str(configured)], check=False)
    after = child_directories(output_root)

    if result.returncode == 0:
        output = newest_new_directory(before, after)
        if output is not None:
            record_output(output)
            print(f"New output folder: {output}")
            if not args.no_open_output:
                open_output(output)
        else:
            print("No new output folder detected.")
    else:
        removed, retained = cleanup_empty_new_directories(before, after)
        for path in removed:
            print(f"Removed empty failed output folder: {path}")
        for path in retained:
            print(f"Retained non-empty partial output for inspection: {path}")

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
