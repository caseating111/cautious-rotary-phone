from __future__ import annotations

import importlib.util
import json
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCRIPT = REPO_ROOT / "existing scripts clean" / "make_matrices.py"


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = ["crop_output", "matrix_output", "grid_csv", "images_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


def load_existing_matrix_script():
    spec = importlib.util.spec_from_file_location("existing_make_matrices", MATRIX_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load matrix script: {MATRIX_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    config = load_config()
    matrix = load_existing_matrix_script()

    # Override only the editable path/settings layer; keep existing matrix logic intact.
    matrix.IMAGE_ROOT = Path(config["crop_output"])
    matrix.GRID_CSV = Path(config["grid_csv"])
    matrix.IMAGES_CSV = Path(config["images_csv"])
    matrix.CONDITION_ORDER_CSV = Path(config["condition_order_csv"])
    matrix.MATRIX_ROOT = Path(config["matrix_output"])
    matrix.MATRIX_OUTPUT = matrix.make_unique_folder(matrix.MATRIX_ROOT, "EXP")
    matrix.ROTATION_MARKER = matrix.IMAGE_ROOT / ".rotated_90ccw.done"

    matrix.main()


if __name__ == "__main__":
    main()
