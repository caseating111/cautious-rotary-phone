from __future__ import annotations

import argparse
import time
from pathlib import Path

try:
    from tools import grid_coordinates
except ModuleNotFoundError:
    import grid_coordinates


def _request(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip().casefold()
    except FileNotFoundError:
        return ""


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def watch(
    handoff: Path,
    asset_directory: Path,
    control_file: Path,
    timeout_seconds: float,
    poll_seconds: float = 0.2,
) -> list[Path]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if grid_coordinates.grid_handoff_has_complete_row(handoff):
            return grid_coordinates.persist_grid_handoff(handoff, asset_directory)
        request = _request(control_file)
        if request == "cancel":
            _discard(handoff)
            return []
        if request == "complete":
            raise SystemExit(
                "Fiji reported completion without a complete grid-coordinate handoff row."
            )
        time.sleep(poll_seconds)
    raise SystemExit("Timed out waiting for Fiji to export accepted grid coordinates.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("asset_directory", type=Path)
    parser.add_argument("control_file", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=7200.0)
    args = parser.parse_args()
    outputs = watch(
        args.handoff,
        args.asset_directory,
        args.control_file,
        args.timeout_seconds,
    )
    if outputs:
        print(f"Saved {len(outputs)} reusable grid coordinate asset(s).")


if __name__ == "__main__":
    main()
