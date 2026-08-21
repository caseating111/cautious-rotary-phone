from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]

MACROS = {
    "alignment": REPO_ROOT / "fiji" / "full_column_alignment.ijm",
    "visibility": REPO_ROOT / "fiji" / "apply_global_visibility.ijm",
}


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    fiji = str(data.get("fiji_executable", "")).strip()
    if not fiji:
        raise SystemExit("Fiji executable is not configured.")
    return data


def macro_argument(alias: str, config: dict) -> str:
    if alias == "alignment":
        tolerance = float(config.get("alignment_tolerance", 0.08))
        if tolerance <= 0:
            raise SystemExit("alignment_tolerance must be positive.")
        return f"cols=10;rows=8;tolerance={tolerance:g}"

    band = float(config.get("visibility_band", 50))
    black_offset = float(config.get("visibility_black_offset", 3))
    high_percentile = float(config.get("visibility_high_percentile", 99.5))
    if band < 1:
        raise SystemExit("visibility_band must be at least 1.")
    if high_percentile <= 0 or high_percentile > 100:
        raise SystemExit("visibility_high_percentile must be >0 and <=100.")
    return f"band={band:g};black_offset={black_offset:g};high_percentile={high_percentile:g}"


def build_command(alias: str, config: dict) -> list[str]:
    return [
        str(Path(config["fiji_executable"])),
        "-macro",
        str(MACROS[alias]),
        macro_argument(alias, config),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("macro", choices=sorted(MACROS))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    command = build_command(args.macro, config)

    if args.dry_run:
        print("COMMAND")
        for part in command:
            print(part)
        return

    fiji = Path(config["fiji_executable"])
    macro = MACROS[args.macro]
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    if not macro.is_file():
        raise SystemExit(f"Macro not found: {macro}")

    subprocess.Popen(command)


if __name__ == "__main__":
    main()
