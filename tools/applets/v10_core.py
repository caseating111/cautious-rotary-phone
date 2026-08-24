from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def clean(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def positive_integer(value: Any, field: str) -> int:
    if value is None or pd.isna(value):
        raise ValueError(f"Missing required {field}.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer, got {value!r}.") from exc
    if not number.is_integer() or number < 1:
        raise ValueError(f"{field} must be a positive integer, got {value!r}.")
    return int(number)


def require_columns(frame: pd.DataFrame, sheet: str, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(
            f"{sheet} is missing required column(s): {', '.join(missing)}."
        )


def validate_project_records(project: dict[str, Any]) -> None:
    session_uids: set[str] = set()
    for index, session in enumerate(project.get("sessions", []), start=1):
        uid = clean(session.get("session_uid"))
        if not uid:
            raise ValueError(f"Session row {index} has a missing sessionUID.")
        if uid in session_uids:
            raise ValueError(f"Duplicate sessionUID: {uid}.")
        session_uids.add(uid)
        if not clean(session.get("exp")) or not clean(session.get("date")):
            raise ValueError(f"Session {uid} is missing Exp or Date.")

    image_uids: set[str] = set()
    positions: set[tuple[str, int]] = set()
    for index, image in enumerate(project.get("images", []), start=1):
        uid = clean(image.get("image_uid"))
        if not uid:
            raise ValueError(f"Master Registry row {index} has a missing Image UID.")
        if uid in image_uids:
            raise ValueError(f"Duplicate Image UID: {uid}.")
        image_uids.add(uid)
        session_uid = clean(image.get("session_uid"))
        if not session_uid:
            raise ValueError(f"Image UID {uid} has a missing sessionUID.")
        if session_uid not in session_uids:
            raise ValueError(
                f"Image UID {uid} references unknown sessionUID {session_uid}."
            )
        image_number = positive_integer(image.get("image_number"), f"Image # for {uid}")
        position = (session_uid, image_number)
        if position in positions:
            raise ValueError(
                f"Duplicate Image # {image_number} in sessionUID {session_uid}."
            )
        positions.add(position)
        for field, label in (("original", "Original"), ("exp", "Exp"), ("set", "Set")):
            if not clean(image.get(field)):
                raise ValueError(f"Image UID {uid} has a missing {label} value.")


def profile_labels(
    rows: pd.DataFrame,
    profile: str,
    *,
    set_value: str | None = None,
) -> list[dict[str, Any]]:
    selected = rows[rows["profile"] == profile]
    if set_value is not None:
        selected = selected[selected["set"] == set_value]
    if selected.empty:
        raise ValueError(f"Assigned profile {profile!r} has no label rows.")
    labels: list[dict[str, Any]] = []
    positions: set[int] = set()
    for _, row in selected.iterrows():
        pos = positive_integer(row["pos"], f"Pos in profile {profile}")
        label = clean(row["label"])
        if label is None:
            raise ValueError(f"Profile {profile!r} has a missing label at Pos {pos}.")
        if pos in positions:
            raise ValueError(f"Profile {profile!r} has duplicate Pos {pos}.")
        positions.add(pos)
        labels.append({"pos": pos, "label": label})
    labels.sort(key=lambda item: item["pos"])
    actual = [item["pos"] for item in labels]
    expected = list(range(1, actual[-1] + 1))
    if actual != expected:
        raise ValueError(
            f"Profile {profile!r} Pos values must be contiguous 1..{expected[-1]}."
        )
    return labels


def row_ranges(
    annotation_set: str,
    grid_rows: int,
    band_count: int,
    overrides: dict[str, list[tuple[int, int]]] | None,
) -> tuple[list[tuple[int, int]], str]:
    if overrides and annotation_set in overrides:
        ranges = [(int(start), int(end)) for start, end in overrides[annotation_set]]
        if len(ranges) != band_count:
            raise ValueError(
                f"Annotation set {annotation_set!r} has {band_count} bands but {len(ranges)} row overrides."
            )
        provenance = "explicit_override"
    elif band_count == 1:
        ranges = [(1, grid_rows)]
        provenance = "full_rows"
    else:
        if grid_rows % band_count:
            raise ValueError(
                f"Annotation set {annotation_set!r} has {grid_rows} rows which cannot be evenly divided "
                f"among {band_count} ordered strain profiles; provide row_band_overrides."
            )
        size = grid_rows // band_count
        ranges = [(index * size + 1, (index + 1) * size) for index in range(band_count)]
        provenance = "even_split"
    occupied: list[int] = []
    for start, end in ranges:
        if start < 1 or end < start or end > grid_rows:
            raise ValueError(f"Invalid row range {start}..{end} for {grid_rows} rows.")
        occupied.extend(range(start, end + 1))
    if sorted(occupied) != list(range(1, grid_rows + 1)):
        raise ValueError(
            f"Row ranges for annotation set {annotation_set!r} must cover rows 1..{grid_rows} exactly once."
        )
    return ranges, provenance


def extract_layouts(
    excel_path: str,
    row_band_overrides: dict[str, list[tuple[int, int]]] | None = None,
    *,
    return_diagnostics: bool = False,
) -> Any:
    frame = pd.read_excel(excel_path, "Annotations", header=1, engine="openpyxl")
    require_columns(
        frame,
        "Annotations",
        [
            "annotationSet",
            "Type",
            "Profile",
            "Order",
            "labels_strain",
            "Pos",
            "labels_vertical",
            "Pos.1",
        ],
    )
    strain_profile_column = (
        "Profile*"
        if "Profile*" in frame and frame["Profile*"].notna().any()
        else "Strain profile"
    )
    strain_set_column = (
        "Set*" if "Set*" in frame and frame["Set*"].notna().any() else "Set"
    )
    vertical_profile_column = (
        "Profile*.1"
        if "Profile*.1" in frame and frame["Profile*.1"].notna().any()
        else "Vertical profile"
    )
    require_columns(
        frame,
        "Annotations",
        [strain_profile_column, strain_set_column, vertical_profile_column],
    )

    assignments = (
        frame[["annotationSet", "Type", "Profile", "Order"]]
        .dropna(subset=["annotationSet", "Type", "Profile"])
        .copy()
    )
    assignments["annotation_set"] = assignments["annotationSet"].map(clean)
    assignments["type"] = assignments["Type"].map(
        lambda value: (clean(value) or "").casefold()
    )
    assignments["profile"] = assignments["Profile"].map(clean)

    strain_rows = frame[
        [strain_profile_column, strain_set_column, "labels_strain", "Pos"]
    ].copy()
    strain_rows.columns = ["profile", "set", "label", "pos"]
    strain_rows["profile"] = strain_rows["profile"].ffill().map(clean)
    strain_rows["set"] = strain_rows["set"].ffill().map(clean)
    strain_rows = strain_rows.dropna(subset=["profile", "label", "pos"])

    vertical_rows = frame[[vertical_profile_column, "labels_vertical", "Pos.1"]].copy()
    vertical_rows.columns = ["profile", "label", "pos"]
    vertical_rows["profile"] = vertical_rows["profile"].ffill().map(clean)
    vertical_rows["set"] = None
    vertical_rows = vertical_rows.dropna(subset=["profile", "label", "pos"])

    layouts: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, str]] = []
    for annotation_set, group in assignments.groupby("annotation_set", sort=False):
        vertical_assignments = group[group["type"] == "vertical"]
        if len(vertical_assignments) != 1:
            raise ValueError(
                f"Annotation set {annotation_set!r} must assign exactly one vertical profile; found {len(vertical_assignments)}."
            )
        vertical_profile = vertical_assignments.iloc[0]["profile"]
        vertical_labels = profile_labels(vertical_rows, vertical_profile)
        grid_rows = vertical_labels[-1]["pos"]

        strain_assignments = group[group["type"] == "strain"].copy()
        if strain_assignments.empty:
            raise ValueError(
                f"Annotation set {annotation_set!r} has no strain profile assignment."
            )
        orders: list[int] = []
        for _, assignment in strain_assignments.iterrows():
            raw_order = assignment["Order"]
            orders.append(
                1
                if len(strain_assignments) == 1 and pd.isna(raw_order)
                else positive_integer(
                    raw_order, f"Order for annotation set {annotation_set}"
                )
            )
        if len(set(orders)) != len(orders) or sorted(orders) != list(
            range(1, len(orders) + 1)
        ):
            raise ValueError(
                f"Annotation set {annotation_set!r} strain-profile Order values must be unique 1..{len(orders)}."
            )
        strain_assignments["resolved_order"] = orders
        strain_assignments = strain_assignments.sort_values("resolved_order")

        band_specs: list[dict[str, Any]] = []
        used_legacy_mapping = False
        for _, assignment in strain_assignments.iterrows():
            profile = assignment["profile"]
            profile_rows = strain_rows[strain_rows["profile"] == profile]
            set_values = list(
                dict.fromkeys(value for value in profile_rows["set"].tolist() if value)
            )
            duplicate_positions = profile_rows["pos"].duplicated().any()
            if (
                len(strain_assignments) == 1
                and len(set_values) > 1
                and duplicate_positions
            ):
                used_legacy_mapping = True
                diagnostics.append(
                    {
                        "code": "LEGACY_SET_BLOCK_BANDS",
                        "annotation_set": annotation_set,
                        "message": "Mapped legacy machine Set* blocks to ordered bands; canonical workbooks should assign distinct profiles with Order.",
                    }
                )
                for set_value in set_values:
                    labels = profile_labels(strain_rows, profile, set_value=set_value)
                    band_specs.append(
                        {"profile": f"{profile} [Set {set_value}]", "labels": labels}
                    )
            else:
                band_specs.append(
                    {"profile": profile, "labels": profile_labels(strain_rows, profile)}
                )

        ranges, mapping = row_ranges(
            annotation_set, grid_rows, len(band_specs), row_band_overrides
        )
        if used_legacy_mapping and mapping == "even_split":
            mapping = "legacy_set_blocks_even_split"
        bands = []
        for index, (spec, (row_start, row_end)) in enumerate(
            zip(band_specs, ranges), start=1
        ):
            local_cols = spec["labels"][-1]["pos"]
            bands.append(
                {
                    "order": index,
                    "profile": spec["profile"],
                    "row_start": row_start,
                    "row_end": row_end,
                    "local_grid_cols": local_cols,
                    "row_mapping_provenance": mapping,
                    "labels": spec["labels"],
                }
            )
        layouts[annotation_set] = {
            "contract_version": 1,
            "layout_id": annotation_set,
            "grid_rows": grid_rows,
            "grid_cols": max(band["local_grid_cols"] for band in bands),
            "vertical_labels": vertical_labels,
            "strain_bands": bands,
        }
    return (layouts, diagnostics) if return_diagnostics else layouts


def build_project_model(records: dict[str, Any], excel_path: str) -> dict[str, Any]:
    if not Path(excel_path).is_file():
        raise ValueError(f"V10 workbook does not exist: {excel_path}")
    validate_project_records(records)
    layouts, diagnostics = extract_layouts(excel_path, return_diagnostics=True)
    assigned = {
        image.get("annotation_set")
        for image in records["images"]
        if image.get("annotation_set")
    }
    missing = sorted(value for value in assigned if value not in layouts)
    if missing:
        raise ValueError(
            f"Image records reference missing annotationSet layout(s): {', '.join(missing)}."
        )
    records["layouts"] = layouts
    records["diagnostics"] = diagnostics
    return records
