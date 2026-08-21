from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
LAST_OUTPUT_FILE = APP_DIR / "last_pillow_output.txt"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "existing scripts clean"

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

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out = APP_DIR / f"{source_path.stem}.configured.py"
    out.write_text(source, encoding="utf-8")
    return out


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
