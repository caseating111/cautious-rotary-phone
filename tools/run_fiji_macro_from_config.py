from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG_FILE = APP_DIR / "config.json"
REPO_ROOT = Path(__file__).resolve().parents[1]

MACROS = {
    "alignment": REPO_ROOT / "fiji" / "full_column_alignment.ijm",
    "visibility": REPO_ROOT / "fiji" / "apply_global_visibility.ijm",
}


def load_config() -> dict:
    if not CONFIG_FILE.is_file():
        raise SystemExit(f"Config not found: {CONFIG_FILE}")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
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
    return (
        f"band={band:g};black_offset={black_offset:g};"
        f"high_percentile={high_percentile:g}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("macro", choices=sorted(MACROS))
    args = parser.parse_args()

    config = load_config()
    fiji = Path(config["fiji_executable"])
    macro = MACROS[args.macro]
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    if not macro.is_file():
        raise SystemExit(f"Macro not found: {macro}")

    subprocess.Popen([str(fiji), "-macro", str(macro), macro_argument(args.macro, config)])


if __name__ == "__main__":
    main()
