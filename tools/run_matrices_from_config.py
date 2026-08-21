from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCRIPT = REPO_ROOT / "existing scripts clean" / "make_matrices.py"
CONFIGURED_SCRIPT = APP_DIR / "make_matrices.configured.py"


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = ["crop_output", "matrix_output", "grid_csv", "images_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


def py_path(value: str) -> str:
    return repr(str(Path(value)))


def configure_script(config: dict) -> Path:
    source = MATRIX_SCRIPT.read_text(encoding="utf-8")
    replacements = {
        'IMAGE_ROOT = Path(r"path here")': f"IMAGE_ROOT = Path({py_path(config['crop_output'])})",
        'GRID_CSV = Path(r"path here")': f"GRID_CSV = Path({py_path(config['grid_csv'])})",
        'IMAGES_CSV = Path(r"path here")': f"IMAGES_CSV = Path({py_path(config['images_csv'])})",
        'CONDITION_ORDER_CSV = Path(r"path here")': f"CONDITION_ORDER_CSV = Path({py_path(config['condition_order_csv'])})",
        'MATRIX_ROOT = Path(r"path here")': f"MATRIX_ROOT = Path({py_path(config['matrix_output'])})",
    }

    for old, new in replacements.items():
        if source.count(old) != 1:
            raise SystemExit(f"Expected one matrix-script setting line, found {source.count(old)}: {old}")
        source = source.replace(old, new, 1)

    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGURED_SCRIPT.write_text(source, encoding="utf-8")
    return CONFIGURED_SCRIPT


def main() -> None:
    configured = configure_script(load_config())
    result = subprocess.run([sys.executable, str(configured)], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
