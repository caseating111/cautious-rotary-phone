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

    for section in ("arrangements", "annotation_assignments"):
        for index, record in enumerate(project.get(section, []), start=1):
            check = clean(record.get("check"))
            if check is not None and check.casefold() != "ok":
                raise ValueError(
                    f"V10 {section} row {index} reports Check={check!r}."
                )
    for profile_type, rows in project.get("annotation_profiles", {}).items():
        keys: set[str] = set()
        profile_positions: dict[tuple[str, str], set[int]] = {}
        for index, record in enumerate(rows, start=1):
            check = clean(record.get("check"))
            if check is not None and check.casefold() != "ok":
                raise ValueError(
                    f"V10 {profile_type} profile row {index} reports Check={check!r}."
                )
            key = clean(record.get("key"))
            if key and key.casefold() in keys:
                raise ValueError(
                    f"Duplicate V10 {profile_type} profile machine Key*: {key}."
                )
            if key:
                keys.add(key.casefold())
            profile = clean(record.get("profile"))
            label = clean(record.get("label"))
            if not profile or label is None:
                raise ValueError(
                    f"V10 {profile_type} profile row {index} has a missing Profile or label."
                )
            position = positive_integer(
                record.get("pos"), f"Pos in {profile_type} profile {profile}"
            )
            identity = (
                profile.casefold(),
                (clean(record.get("set")) or "").casefold(),
            )
            positions_for_profile = profile_positions.setdefault(identity, set())
            if position in positions_for_profile:
                raise ValueError(
                    f"V10 {profile_type} profile {profile!r} Set "
                    f"{record.get('set')!r} has duplicate Pos {position}."
                )
            positions_for_profile.add(position)
        for (profile, set_value), positions_for_profile in profile_positions.items():
            expected = set(range(1, max(positions_for_profile) + 1))
            if positions_for_profile != expected:
                suffix = f" Set {set_value!r}" if set_value else ""
                raise ValueError(
                    f"V10 {profile_type} profile {profile!r}{suffix} Pos values "
                    f"must be contiguous 1..{max(positions_for_profile)}."
                )

    profile_names = {
        profile_type: {
            str(record["profile"]).casefold()
            for record in rows
            if clean(record.get("profile"))
        }
        for profile_type, rows in project.get("annotation_profiles", {}).items()
    }
    assignment_identities: set[tuple[str, str, int]] = set()
    for record in project.get("annotation_assignments", []):
        annotation_set = clean(record.get("annotation_set"))
        profile_type = (clean(record.get("type")) or "").casefold()
        profile = clean(record.get("profile"))
        if (
            not annotation_set
            or profile_type not in {"strain", "vertical", "other"}
            or not profile
        ):
            raise ValueError("V10 annotation assignment has missing or unknown metadata.")
        order = positive_integer(
            record.get("order"),
            f"Order for annotation set {annotation_set} {profile_type} profile {profile}",
        )
        identity = (annotation_set.casefold(), profile_type, order)
        if identity in assignment_identities:
            raise ValueError(
                f"V10 {profile_type} Order values must be unique in annotation set "
                f"{annotation_set!r}; duplicate Order {order}."
            )
        assignment_identities.add(identity)
        if profile.casefold() not in profile_names.get(profile_type, set()):
            raise ValueError(
                f"Annotation set {annotation_set!r} assigns missing {profile_type} "
                f"profile {profile!r}."
            )

    arrangements = project.get("arrangements", [])
    if arrangements:
        arrangement_map: dict[tuple[str, int], dict[str, Any]] = {}
        for record in arrangements:
            identity = (
                str(record["arrangement"]).casefold(),
                int(record["image_number"]),
            )
            if identity in arrangement_map:
                raise ValueError(
                    "Duplicate Arrangements identity: "
                    f"{record['arrangement']} Image # {record['image_number']}."
                )
            arrangement_map[identity] = record
        for image in project.get("images", []):
            identity = (
                str(image.get("arrangement") or "").casefold(),
                int(image["image_number"]),
            )
            arrangement = arrangement_map.get(identity)
            if arrangement is None:
                raise ValueError(
                    f"Image UID {image['image_uid']} has no matching Arrangements row."
                )
            for field in ("sample_description", "set", "media", "condition", "rep"):
                if image.get(field) != arrangement.get(field):
                    raise ValueError(
                        f"Image UID {image['image_uid']} disagrees with Arrangements "
                        f"for {field}: {image.get(field)!r} versus "
                        f"{arrangement.get(field)!r}."
                    )

    sessions_by_uid = {
        str(session["session_uid"]): session for session in project.get("sessions", [])
    }
    for image in project.get("images", []):
        session = sessions_by_uid[str(image["session_uid"])]
        for field in ("exp", "date", "time", "arrangement", "annotation_set", "id"):
            session_value = session.get(field)
            image_value = image.get(field)
            if (
                session_value is not None
                and image_value is not None
                and image_value != session_value
            ):
                raise ValueError(
                    f"Image UID {image['image_uid']} disagrees with Overview session "
                    f"{image['session_uid']} for {field}: {image_value!r} versus "
                    f"{session_value!r}."
                )


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

        # Ordered strain-profile assignments define physical top-to-bottom row
        # bands.  Set values inside a profile are label variants selected by an
        # image's Master Registry Set; they are not additional physical bands.
        band_specs: list[dict[str, Any]] = []
        for _, assignment in strain_assignments.iterrows():
            profile = assignment["profile"]
            profile_rows = strain_rows[strain_rows["profile"] == profile]
            set_values = list(
                dict.fromkeys(value for value in profile_rows["set"].tolist() if value)
            )
            if set_values:
                label_sets = {
                    set_value: profile_labels(
                        strain_rows, profile, set_value=set_value
                    )
                    for set_value in set_values
                }
                labels = label_sets[set_values[0]]
                if len(label_sets) > 1:
                    diagnostics.append(
                        {
                            "code": "SET_LABEL_VARIANTS",
                            "annotation_set": annotation_set,
                            "message": (
                                f"Strain profile {profile!r} has Set-specific label "
                                "variants; each image resolves the variant matching its Set."
                            ),
                        }
                    )
                band_specs.append(
                    {
                        "profile": profile,
                        "labels": labels,
                        "label_sets": label_sets,
                    }
                )
            else:
                labels = profile_labels(strain_rows, profile)
                band_specs.append({"profile": profile, "labels": labels})

        ranges, mapping = row_ranges(
            annotation_set, grid_rows, len(band_specs), row_band_overrides
        )
        bands = []
        for index, (spec, (row_start, row_end)) in enumerate(
            zip(band_specs, ranges), start=1
        ):
            label_sets = spec.get("label_sets", {})
            local_cols = max(
                labels[-1]["pos"]
                for labels in [spec["labels"], *list(label_sets.values())]
            )
            band = {
                "order": index,
                "profile": spec["profile"],
                "row_start": row_start,
                "row_end": row_end,
                "local_grid_cols": local_cols,
                "row_mapping_provenance": mapping,
                "labels": spec["labels"],
            }
            if label_sets:
                band["label_sets"] = label_sets
            bands.append(band)
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
    unresolved: set[tuple[str, str, str]] = set()
    for image in records["images"]:
        annotation_set = clean(image.get("annotation_set"))
        image_set = clean(image.get("set")) or ""
        if not annotation_set or annotation_set not in layouts:
            continue
        for band in layouts[annotation_set].get("strain_bands", []):
            label_sets = band.get("label_sets") or {}
            if (
                len(label_sets) > 1
                and image_set.casefold()
                not in {str(value).casefold() for value in label_sets}
            ):
                unresolved.add(
                    (annotation_set, image_set, str(band.get("profile") or ""))
                )
    for annotation_set, image_set, profile in sorted(unresolved):
        diagnostics.append(
            {
                "code": "UNRESOLVED_IMAGE_LABEL_SET",
                "annotation_set": annotation_set,
                "message": (
                    f"Image Set {image_set!r} has no matching label variant in "
                    f"strain profile {profile!r}; grid-dependent actions for those "
                    "images require a workbook correction or explicit mapping."
                ),
            }
        )
    records["layouts"] = layouts
    records["diagnostics"] = diagnostics
    return records
