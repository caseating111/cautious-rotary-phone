from __future__ import annotations

try:
    from tools.custom_matrix_preview import PreviewResult
except ModuleNotFoundError:
    from custom_matrix_preview import PreviewResult


def build_preview(selection: dict) -> PreviewResult:
    del selection
    raise SystemExit(
        "Presentation-normalized previews are retired because their archived full-column "
        "display-range producer is not part of the current four-point workflow. Use Raw display mode."
    )
