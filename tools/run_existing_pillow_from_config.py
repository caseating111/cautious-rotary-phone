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

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
LAST_OUTPUT_FILE = APP_DIR / "last_pillow_output.txt"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "existing scripts clean"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

SCRIPTS = {
    "matrices": "make_matrices.py",
    "all-strains": "allstrain matrix.py",
    "all-strains-dedup": "allstrainmatrix extra WT removed.py",
    "label-individual": "folder per strain all indiv strains labelled.py",
}


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = ["crop_output", "matrix_output", "grid_csv", "images_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    try:
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid crop dimensions: {exc}") from exc
    if data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Crop dimensions must be positive.")
    return data


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


def expected_crop_prefixes(grid_path: Path, images_path: Path) -> set[str]:
    grid = read_csv_rows(grid_path)
    images = read_csv_rows(images_path)
    columns_by_grid: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in grid:
        try:
            column = int(row.get("Column", ""))
        except ValueError as exc:
            raise SystemExit(f"Invalid grid column in {grid_path}: {row.get('Column', '')!r}") from exc
        columns_by_grid[(row.get("Experiment", ""), row.get("Set", ""))].add(column)

    prefixes: set[str] = set()
    for row in images:
        exp = row.get("Experiment", "")
        set_name = row.get("Set", "")
        type_name = row.get("Type", "")
        for column in columns_by_grid.get((exp, set_name), set()):
            for state in ("Top", "Low"):
                prefixes.add(f"{exp}_{set_name}_{type_name}_{column:02d}_{state}_".lower())
    return prefixes


def validate_unique_crop_matches(root: Path, grid_path: Path, images_path: Path) -> None:
    if not root.is_dir():
        raise SystemExit(f"Crop output folder not found: {root}")

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    prefixes = expected_crop_prefixes(grid_path, images_path)
    ambiguous: list[tuple[str, list[Path]]] = []

    for prefix in sorted(prefixes):
        matches = [path for path in files if path.stem.lower().startswith(prefix)]
        if len(matches) > 1:
            ambiguous.append((prefix, matches))

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


def normalize_crop_orientation(root: Path, crop_width: int, crop_height: int) -> tuple[int, int, int]:
    if not root.is_dir():
        raise SystemExit(f"Crop output folder not found: {root}")
    if crop_width == crop_height:
        raise SystemExit("Automatic crop-orientation normalization requires non-square crop dimensions.")

    unrotated = (crop_width, crop_height)
    rotated_size = (crop_height, crop_width)
    rotated = 0
    already_ready = 0
    unexpected = 0

    for path in sorted(root.rglob("*.png")):
        if not path.is_file():
            continue
        try:
            with Image.open(path) as image:
                size = image.size
                if size == unrotated:
                    turned = image.transpose(Image.Transpose.ROTATE_90)
                    turned.save(path)
                    rotated += 1
                elif size == rotated_size:
                    already_ready += 1
                else:
                    unexpected += 1
        except OSError as exc:
            raise SystemExit(f"Could not inspect/rotate crop {path}: {exc}") from exc

    print(
        "Crop orientation: "
        f"rotated {rotated}, already ready {already_ready}, unexpected-size PNGs {unexpected}"
    )
    return rotated, already_ready, unexpected


def child_directories(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {path.resolve() for path in root.iterdir() if path.is_dir()}


def newest_new_directory(before: set[Path], after: set[Path]) -> Path | None:
    created = [path for path in after - before if path.is_dir()]
    if not created:
        return None
    return max(created, key=lambda path: path.stat().st_mtime_ns)


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
    args = parser.parse_args()

    config = load_config()
    crop_root = Path(config["crop_output"])
    validate_unique_crop_matches(crop_root, Path(config["grid_csv"]), Path(config["images_csv"]))
    normalize_crop_orientation(crop_root, config["crop_width"], config["crop_height"])

    output_root = Path(config["matrix_output"])
    before = child_directories(output_root)
    configured = configured_copy(args.script, config)
    result = subprocess.run([sys.executable, str(configured)], check=False)

    if result.returncode == 0:
        output = newest_new_directory(before, child_directories(output_root))
        if output is not None:
            record_output(output)
            print(f"New output folder: {output}")
            if not args.no_open_output:
                open_output(output)
        else:
            print("No new output folder detected.")

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
