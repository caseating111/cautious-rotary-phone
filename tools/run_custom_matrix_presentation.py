from __future__ import annotations

from pathlib import Path


def run_job(selection: dict, no_open_output: bool = False) -> Path:
    del selection, no_open_output
    raise SystemExit(
        "Presentation-normalized custom matrices are retired because their archived full-column "
        "display-range producer is not part of the current four-point workflow. Use Raw display mode."
    )
