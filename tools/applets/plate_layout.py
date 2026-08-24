import os
from typing import Any, Dict, List, Optional, Tuple, Union

from .v10_adapter import load_v10, extract_layouts, derive_plate_layout as adapter_derive_layout


def validate_plate_layout(layout: Dict[str, Any]) -> bool:
    """
    Validates a PlateLayout dictionary against contracts/plate_layout.schema.json v1 rules:
    - contract_version must be 1
    - layout_id must be non-empty string
    - grid_rows and grid_cols must be >= 1
    - vertical_labels must have length equal to grid_rows with valid pos 1..grid_rows
    - strain_bands must have >= 1 band
    - strain_bands row_start and row_end must be within 1..grid_rows and non-overlapping
    - all band labels must have valid pos >= 1
    """
    if not isinstance(layout, dict):
        raise ValueError("PlateLayout must be a dictionary")
    if layout.get("contract_version") != 1:
        raise ValueError(f"Unsupported contract_version: {layout.get('contract_version')}")
    if not layout.get("layout_id") or not isinstance(layout["layout_id"], str):
        raise ValueError("layout_id must be a non-empty string")

    rows = layout.get("grid_rows")
    cols = layout.get("grid_cols")
    if not isinstance(rows, int) or rows < 1:
        raise ValueError(f"grid_rows must be an integer >= 1, got {rows}")
    if not isinstance(cols, int) or cols < 1:
        raise ValueError(f"grid_cols must be an integer >= 1, got {cols}")

    v_labels = layout.get("vertical_labels")
    if not isinstance(v_labels, list) or len(v_labels) == 0:
        raise ValueError("vertical_labels must be a non-empty list")

    v_positions = [v["pos"] for v in v_labels]
    if sorted(v_positions) != list(range(1, rows + 1)):
        raise ValueError(f"vertical_labels positions must be 1..{rows}, got {v_positions}")

    bands = layout.get("strain_bands")
    if not isinstance(bands, list) or len(bands) == 0:
        raise ValueError("strain_bands must have at least one band")

    occupied_rows = set()
    max_band_col = 0
    band_orders = []

    for idx, b in enumerate(bands):
        order = b.get("order")
        r_start = b.get("row_start")
        r_end = b.get("row_end")
        labels = b.get("labels")

        if not isinstance(order, int) or order < 1:
            raise ValueError(f"Band order must be an integer >= 1, got {order}")
        band_orders.append(order)
        if not isinstance(r_start, int) or not isinstance(r_end, int) or r_start < 1 or r_end < r_start or r_end > rows:
            raise ValueError(f"Invalid row range ({r_start}, {r_end}) for grid_rows={rows}")

        # Check overlapping rows
        band_rows = set(range(r_start, r_end + 1))
        if occupied_rows.intersection(band_rows):
            raise ValueError(f"Overlapping row allocation detected in band order {order}: {band_rows.intersection(occupied_rows)}")
        occupied_rows.update(band_rows)

        if not isinstance(labels, list) or len(labels) == 0:
            raise ValueError(f"Band order {order} has no labels")

        band_positions = [lbl["pos"] for lbl in labels]
        if len(band_positions) != len(set(band_positions)):
            raise ValueError(f"Duplicate positions found in band order {order}: {band_positions}")

        max_band_col = max(max_band_col, max(band_positions))
        local_cols = b.get("local_grid_cols")
        if local_cols is not None and local_cols != max(band_positions):
            raise ValueError(f"Band order {order} local_grid_cols does not match its widest Pos")

    if sorted(band_orders) != list(range(1, len(bands) + 1)):
        raise ValueError(f"Band orders must be unique and sequential 1..{len(bands)}, got {band_orders}")
    if occupied_rows != set(range(1, rows + 1)):
        raise ValueError(f"Strain bands must cover every physical row 1..{rows} exactly once")


    if max_band_col != cols:
        raise ValueError(f"grid_cols ({cols}) does not match widest strain band width ({max_band_col})")

    return True


def derive_plate_layout_from_spec(
    layout_id: str,
    vertical_labels: List[Dict[str, Any]],
    strain_bands_spec: List[Dict[str, Any]],
    row_band_overrides: Optional[List[Tuple[int, int]]] = None
) -> Dict[str, Any]:
    """
    Derives a canonical PlateLayout v1 dictionary from structured specification data.

    Arguments:
    - layout_id: Identifier for the layout (e.g. 'annotationSet 1' or '1')
    - vertical_labels: List of dicts [{'pos': 1, 'label': '0'}, ...]
    - strain_bands_spec: List of dicts [{'order': 1, 'profile': 'P1', 'labels': [...]}, ...]
    - row_band_overrides: Optional list of (row_start, row_end) tuples per band
    """
    if not vertical_labels:
        raise ValueError("Vertical labels are required to determine physical rows")

    grid_rows = max(v["pos"] for v in vertical_labels)
    num_bands = len(strain_bands_spec)
    if num_bands == 0:
        raise ValueError("At least one strain band specification is required")

    # Determine row distribution
    if row_band_overrides:
        if len(row_band_overrides) != num_bands:
            raise ValueError(f"row_band_overrides length ({len(row_band_overrides)}) does not match number of bands ({num_bands})")
        row_ranges = row_band_overrides
        row_mapping_provenance = "explicit_override"
    elif num_bands == 1:
        row_ranges = [(1, grid_rows)]
        row_mapping_provenance = "full_rows"
    else:
        if grid_rows % num_bands != 0:
            raise ValueError(
                f"Cannot evenly divide {grid_rows} physical rows across {num_bands} strain bands. "
                f"Please provide explicit row_band_overrides, e.g. [(1, 4), (5, 8)]."
            )
        band_size = grid_rows // num_bands
        row_ranges = []
        for i in range(num_bands):
            r_start = i * band_size + 1
            r_end = (i + 1) * band_size
            row_ranges.append((r_start, r_end))
        row_mapping_provenance = "even_split"

    # Sort strain bands by order
    sorted_specs = sorted(strain_bands_spec, key=lambda s: s.get("order", 1))

    strain_bands = []
    max_cols = 0

    for idx, spec in enumerate(sorted_specs):
        r_start, r_end = row_ranges[idx]
        labels = spec.get("labels", [])
        if not labels:
            raise ValueError(f"Strain band at order {spec.get('order')} has no labels")

        # Authoritative ordering by pos
        sorted_labels = sorted(labels, key=lambda l: l["pos"])
        band_max = max(l["pos"] for l in sorted_labels)
        max_cols = max(max_cols, band_max)

        strain_bands.append({
            "order": spec.get("order", idx + 1),
            "profile": spec.get("profile"),
            "row_start": r_start,
            "row_end": r_end,
            "local_grid_cols": band_max,
            "row_mapping_provenance": row_mapping_provenance,
            "labels": [{"pos": l["pos"], "label": str(l["label"])} for l in sorted_labels]
        })

    # Sort vertical labels by pos
    sorted_vert = sorted(vertical_labels, key=lambda v: v["pos"])

    layout = {
        "contract_version": 1,
        "layout_id": str(layout_id),
        "grid_rows": grid_rows,
        "grid_cols": max_cols,
        "vertical_labels": [{"pos": v["pos"], "label": str(v["label"])} for v in sorted_vert],
        "strain_bands": strain_bands
    }

    validate_plate_layout(layout)
    return layout


def derive_plate_layout(
    project_or_path: Union[Dict[str, Any], str],
    image_uid: Optional[str] = None,
    layout_id: Optional[str] = None,
    row_band_overrides: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Primary interface for deriving PlateLayout v1 from a ProjectModel or V10 Excel path.

    If given a file path, parses and extracts layouts via V10 adapter.
    If given a ProjectModel:
    - If image_uid is provided: resolves the image's assigned annotationSet and returns its PlateLayout.
    - If layout_id is provided: returns layout for that ID.
    - Otherwise returns the single layout if only 1 exists, or raises ValueError.
    """
    if isinstance(project_or_path, str):
        layouts = extract_layouts(project_or_path, row_band_overrides=row_band_overrides)
        if layout_id:
            lid_clean = str(layout_id).replace("annotationSet", "").strip()
            for k, v in layouts.items():
                k_clean = str(k).replace("annotationSet", "").strip()
                if k == layout_id or k_clean == lid_clean or str(v.get("layout_id")) == str(layout_id):
                    return v
            raise ValueError(f"Layout '{layout_id}' not found in workbook '{project_or_path}'")
        if image_uid:
            pm = load_v10(project_or_path)
            return adapter_derive_layout(pm, image_uid, layouts=layouts)
        if len(layouts) == 1:
            return next(iter(layouts.values()))
        return layouts

    elif isinstance(project_or_path, dict):
        pm = project_or_path
        # If project_model was passed
        if image_uid:
            return adapter_derive_layout(pm, image_uid, row_band_overrides=row_band_overrides if isinstance(row_band_overrides, dict) else None)
        elif layout_id:
            # Look up across project_model metadata if layouts cache attached
            lid_clean = str(layout_id).replace("annotationSet", "").strip()
            # If v10_path in project_model
            v10_p = pm.get("source_file") or pm.get("v10_path")
            if v10_p and os.path.exists(v10_p):
                return derive_plate_layout(v10_p, layout_id=layout_id, row_band_overrides=row_band_overrides)
            raise ValueError(f"Cannot resolve layout_id '{layout_id}' without v10 workbook path or image_uid reference")
        else:
            raise ValueError("Must provide either image_uid or layout_id to derive_plate_layout")
    else:
        raise TypeError(f"Expected dict or str path, got {type(project_or_path)}")
