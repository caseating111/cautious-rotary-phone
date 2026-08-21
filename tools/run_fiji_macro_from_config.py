from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
VISIBILITY_MACRO = REPO_ROOT / "fiji" / "apply_global_visibility.ijm"


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read config.json: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("config.json must contain a JSON object of named settings.")
    fiji = str(data.get("fiji_executable", "")).strip()
    if not fiji:
        raise SystemExit("Fiji executable is not configured.")
    return data


def visibility_argument(config: dict) -> str:
    try:
        band = float(config.get("visibility_band", 50))
        black_offset = float(config.get("visibility_black_offset", 3))
        high_percentile = float(config.get("visibility_high_percentile", 99.5))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid visibility setting: {exc}") from exc
    if not all(math.isfinite(value) for value in (band, black_offset, high_percentile)):
        raise SystemExit("Visibility settings must be finite numbers.")
    if band < 1:
        raise SystemExit("visibility_band must be at least 1.")
    if high_percentile <= 0 or high_percentile > 100:
        raise SystemExit("visibility_high_percentile must be >0 and <=100.")
    return f"band={band:g};black_offset={black_offset:g};high_percentile={high_percentile:g}"


def build_command(config: dict) -> list[str]:
    return [
        str(Path(config["fiji_executable"])),
        "-macro",
        str(VISIBILITY_MACRO),
        visibility_argument(config),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("macro", choices=["visibility"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    command = build_command(config)

    if args.dry_run:
        print("COMMAND")
        for part in command:
            print(part)
        return

    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    if not VISIBILITY_MACRO.is_file():
        raise SystemExit(f"Macro not found: {VISIBILITY_MACRO}")

    subprocess.Popen(command)


if __name__ == "__main__":
    main()
