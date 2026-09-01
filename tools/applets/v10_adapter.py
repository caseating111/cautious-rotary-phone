import copy
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd


def _text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    return str(value).split(" ")[0].strip() if isinstance(value, pd.Timestamp) else str(value).strip()


def _label_text(value: Any) -> Optional[str]:
    """Preserve label text while avoiding pandas' synthetic integer decimals."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def _integer(value: Any) -> Optional[int]:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return int(number) if number.is_integer() else None


def load_v10(excel_path: str) -> Dict[str, Any]:
    """
    Reads a V10 workbook (.xlsm or .xlsx) in read-only mode and produces ProjectModel v1.
    Preserves workbook terminology, prefers resolved machine-readable '*' fields,
    and supports independently optional Media and Condition fields.
    """
    xls = pd.ExcelFile(excel_path, engine="openpyxl")
    df_overview = pd.read_excel(xls, "Overview", header=1)
    df_arrangements = pd.read_excel(xls, "Arrangements", header=1)
    df_annotations = pd.read_excel(xls, "Annotations", header=1)
    df_master = pd.read_excel(xls, "Master Registry", header=1)

    # 1. Parse Sessions
    sessions: List[Dict[str, Any]] = []

    # Filter Overview to included rows if 'Include' column is present
    if "Include" in df_overview.columns:
        overview_included = df_overview[df_overview["Include"] == True].copy()
        if overview_included.empty:
            overview_included = df_overview.dropna(subset=["sessionUID*"]).copy() if "sessionUID*" in df_overview.columns else df_overview.copy()
    else:
        overview_included = df_overview.copy()

    # Determine session records from Overview (fallback to Master Registry)
    session_rows = []
    if "sessionUID*" in overview_included.columns and not overview_included["sessionUID*"].dropna().empty:
        session_df = overview_included.dropna(subset=["sessionUID*"])
        for _, row in session_df.iterrows():
            suid = str(row["sessionUID*"]).strip()
            exp_val = row.get("Exp*") if pd.notnull(row.get("Exp*")) else row.get("Exp")
            exp_str = str(int(exp_val)) if isinstance(exp_val, (int, float)) and not pd.isna(exp_val) and float(exp_val).is_integer() else str(exp_val) if pd.notnull(exp_val) else ""

            raw_date = row.get("Date*") if pd.notnull(row.get("Date*")) else row.get("Date")
            date_str = str(raw_date).split(" ")[0].strip() if pd.notnull(raw_date) else ""

            time_val = row.get("Time")
            time_str = str(time_val).strip() if pd.notnull(time_val) else None

            name_val = row.get("Name*") if pd.notnull(row.get("Name*")) else row.get("Name")
            name_str = str(name_val).strip() if pd.notnull(name_val) else None

            arr_val = row.get("Arrangement*") if pd.notnull(row.get("Arrangement*")) else row.get("Arrangement")
            arr_str = str(arr_val).strip() if pd.notnull(arr_val) else None

            ann_val = row.get("annotationSet*") if pd.notnull(row.get("annotationSet*")) else row.get("annotationSet")
            ann_str = str(ann_val).strip() if pd.notnull(ann_val) else None

            session_rows.append({
                "session_uid": suid,
                "exp": exp_str,
                "date": date_str,
                "date_display": _text(row.get("Date")),
                "time": time_str,
                "name": name_str,
                "name_display": _text(row.get("Name")),
                "arrangement": arr_str,
                "arrangement_display": _text(row.get("Arrangement")),
                "annotation_set": ann_str,
                "annotation_set_display": _text(row.get("annotationSet")),
                "replicate_label": _text(
                    row.get("Replicate label*")
                    if pd.notnull(row.get("Replicate label*"))
                    else row.get("Replicate label")
                ),
                "replicate_label_display": _text(row.get("Replicate label")),
                "description_text": _text(
                    row.get("Description text*")
                    if pd.notnull(row.get("Description text*"))
                    else row.get("Description text")
                ),
                "description_text_display": _text(row.get("Description text")),
                "extension": _text(
                    row.get("Ext*") if pd.notnull(row.get("Ext*")) else row.get("Ext")
                ),
                "extension_display": _text(row.get("Ext")),
                "include": bool(row.get("Include"))
                if pd.notnull(row.get("Include"))
                else None,
                "images_expected": _integer(row.get("Images")),
                "registration_start": _integer(row.get("Reg start")),
                "registration_end": _integer(row.get("Reg end")),
                "status": _text(row.get("Status")),
                "id": _text(row.get("ID")),
            })
    else:
        # Fallback to distinct session records in Master Registry
        unique_sessions = df_master.drop_duplicates(subset=["sessionUID*"]).dropna(subset=["sessionUID*"])
        for _, row in unique_sessions.iterrows():
            suid = str(row["sessionUID*"]).strip()
            exp_val = row.get("Exp")
            exp_str = str(int(exp_val)) if isinstance(exp_val, (int, float)) and not pd.isna(exp_val) and float(exp_val).is_integer() else str(exp_val) if pd.notnull(exp_val) else ""

            raw_date = row.get("Date*") if pd.notnull(row.get("Date*")) else row.get("Date")
            date_str = str(raw_date).split(" ")[0].strip() if pd.notnull(raw_date) else ""

            time_val = row.get("Time")
            time_str = str(time_val).strip() if pd.notnull(time_val) else None

            arr_val = row.get("Arrangement")
            arr_str = str(arr_val).strip() if pd.notnull(arr_val) else None

            ann_val = row.get("annotationSet")
            ann_str = str(ann_val).strip() if pd.notnull(ann_val) else None

            session_rows.append({
                "session_uid": suid,
                "exp": exp_str,
                "date": date_str,
                "time": time_str,
                "name": None,
                "arrangement": arr_str,
                "annotation_set": ann_str,
            })

    # Preserve every source row. Canonical validation must report duplicate
    # sessionUID values instead of silently discarding later/conflicting rows.
    sessions.extend(session_rows)

    # 2. Parse Expected Images from Master Registry
    images: List[Dict[str, Any]] = []
    for _, row in df_master.iterrows():
        raw_uid = row.get("Image UID")
        if pd.isnull(raw_uid) or str(raw_uid).strip() == "":
            continue
        image_uid = str(raw_uid).strip()

        suid_val = row.get("sessionUID*") if pd.notnull(row.get("sessionUID*")) else ""
        session_uid = str(suid_val).strip()

        img_num = _integer(row.get("Image #"))

        orig_val = row.get("Original")
        orig_str = str(orig_val).strip() if pd.notnull(orig_val) else None

        working_fn_val = row.get("Working filename")
        working_fn = str(working_fn_val).strip() if pd.notnull(working_fn_val) else None

        exp_val = row.get("Exp")
        exp_str = str(int(exp_val)) if isinstance(exp_val, (int, float)) and not pd.isna(exp_val) and float(exp_val).is_integer() else str(exp_val) if pd.notnull(exp_val) else ""

        set_val = row.get("Set*") if pd.notnull(row.get("Set*")) else row.get("Set")
        set_str = str(set_val).strip() if pd.notnull(set_val) else ""

        media_val = row.get("Media")
        media_str = str(media_val).strip() if pd.notnull(media_val) else None

        cond_val = row.get("Condition")
        cond_str = str(cond_val).strip() if pd.notnull(cond_val) else None

        rep_val = row.get("Rep #")
        if pd.notnull(rep_val):
            rep: Optional[Union[int, str]] = int(rep_val) if isinstance(rep_val, (int, float)) and float(rep_val).is_integer() else str(rep_val).strip()
        else:
            rep = None

        arr_val = row.get("Arrangement")
        arr_str = str(arr_val).strip() if pd.notnull(arr_val) else None

        ann_val = row.get("annotationSet")
        ann_str = str(ann_val).strip() if pd.notnull(ann_val) else None

        id_val = row.get("ID")
        id_str = str(id_val).strip() if pd.notnull(id_val) else None
        sample_val = row.get("Sample description")
        sample_str = str(sample_val).strip() if pd.notnull(sample_val) else None
        date_val = row.get("Date*") if pd.notnull(row.get("Date*")) else row.get("Date")
        image_date = str(date_val).split(" ")[0].strip() if pd.notnull(date_val) else None
        image_date_display = _text(row.get("Date"))
        image_time = _text(row.get("Time"))
        figure_val = row.get("figureDescriptionLabel")
        figure_str = str(figure_val).strip() if pd.notnull(figure_val) else None
        status_val = row.get("Filename status")
        filename_status = str(status_val).strip() if pd.notnull(status_val) else None

        img_entry = {
            "image_uid": image_uid,
            "session_uid": session_uid,
            "image_number": img_num,
            "original": orig_str,
            "working_filename": working_fn,
            "exp": exp_str,
            "set": set_str,
            "media": media_str,
            "condition": cond_str,
            "rep": rep,
            "arrangement": arr_str,
            "annotation_set": ann_str
            ,"id": id_str
            ,"sample_description": sample_str
            ,"date": image_date
            ,"date_display": image_date_display
            ,"time": image_time
            ,"figure_description_label": figure_str
            ,"filename_status": filename_status
            ,"base_filename": _text(row.get("Base filename*"))
            ,"base_count": _integer(row.get("Base count*"))
            ,"set_filename": _text(row.get("Set filename*"))
            ,"set_filename_count": _integer(row.get("Set filename count*"))
        }
        images.append(img_entry)

    arrangements: List[Dict[str, Any]] = []
    for _, row in df_arrangements.iterrows():
        arrangement = _text(
            row.get("Arrangement*")
            if pd.notnull(row.get("Arrangement*"))
            else row.get("Arrangement")
        )
        image_number = _integer(row.get("Image #"))
        if arrangement is None or image_number is None:
            continue
        arrangements.append(
            {
                "date_display": _text(row.get("Date")),
                "arrangement": arrangement,
                "arrangement_display": _text(row.get("Arrangement")),
                "image_number": image_number,
                "sample_description": _text(row.get("Sample description")),
                "set": _text(row.get("Set")),
                "media": _text(row.get("Media")),
                "condition": _text(row.get("Condition")),
                "condition_machine": _text(row.get("Condition*")),
                "rep": _integer(row.get("Rep #")),
                "group_key": _text(row.get("Group key*")),
                "check": _text(row.get("Check*")),
            }
        )

    annotation_assignments: List[Dict[str, Any]] = []
    for _, row in df_annotations.iterrows():
        annotation_set = _text(row.get("annotationSet"))
        profile = _text(row.get("Profile"))
        type_name = _text(row.get("Type"))
        if not annotation_set or not profile or not type_name:
            continue
        annotation_assignments.append(
            {
                "date_display": _text(row.get("Date")),
                "annotation_set": annotation_set,
                "type": type_name.casefold(),
                "profile": profile,
                "order": _integer(row.get("Order")),
                "check": _text(row.get("Check")),
            }
        )

    annotation_profiles: Dict[str, List[Dict[str, Any]]] = {
        "strain": [],
        "vertical": [],
        "other": [],
    }
    profile_columns = {
        "strain": ("Profile*", "Set*", "labels_strain", "Pos", "Key*", "Check*"),
        "vertical": (
            "Profile*.1",
            "Set*.1",
            "labels_vertical",
            "Pos.1",
            "Key*.1",
            "Check*.1",
        ),
        "other": (
            "Profile*.2",
            "Set*.2",
            "labels_other",
            "Pos.2",
            "Key*.2",
            "Check*.2",
        ),
    }
    for profile_type, columns in profile_columns.items():
        profile_col, set_col, label_col, pos_col, key_col, check_col = columns
        for _, row in df_annotations.iterrows():
            profile = _text(row.get(profile_col))
            position = _integer(row.get(pos_col))
            label = _label_text(row.get(label_col))
            if not profile or position is None or label is None:
                continue
            annotation_profiles[profile_type].append(
                {
                    "profile": profile,
                    "set": _text(row.get(set_col)),
                    "label": label,
                    "pos": position,
                    "key": _text(row.get(key_col)),
                    "check": _text(row.get(check_col)),
                }
            )

    return {
        "contract_version": 1,
        "sessions": sessions,
        "images": images,
        "arrangements": arrangements,
        "annotation_assignments": annotation_assignments,
        "annotation_profiles": annotation_profiles,
    }


def extract_layouts(excel_path: str, row_band_overrides: Optional[Dict[str, List[Tuple[int, int]]]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Reads the Annotations sheet of a V10 workbook and produces normalized PlateLayouts.

    Current Contract Rules:
    - 1 vertical profile per annotationSet; Set inside vertical profile table is ignored.
    - GridRows = maximum vertical Pos.
    - Assigned strain profile(s) define strain-label bands.
    - Distinct populated 'Set' blocks inside the strain table define ordered strain-label bands (top-to-bottom).
    - Strain-table Set values are band markers, NOT filters against Master Registry image Set.
    - GridCols = maximum Pos across all bands.
    - Physical rows are distributed evenly across strain bands when deterministic (e.g. 8 rows / 2 bands -> 1-4, 5-8).
    - If non-deterministic, raises ValueError unless row_band_overrides provides explicit ranges.
    """
    xls = pd.ExcelFile(excel_path, engine="openpyxl")
    df_ann = pd.read_excel(xls, "Annotations", header=1)

    # 1. Parse Annotation Set Assignments
    assignments = df_ann[["annotationSet", "Type", "Profile", "Order"]].dropna(subset=["annotationSet", "Type", "Profile"]).copy()
    assignments["Order"] = pd.to_numeric(assignments["Order"], errors="coerce").fillna(1).astype(int)

    # 2. Parse Vertical Profiles (Ignore Set.1)
    # Prefer machine-resolved columns Profile*.1 if present
    if "Profile*.1" in df_ann.columns and not df_ann["Profile*.1"].dropna().empty:
        df_vert = df_ann[["Profile*.1", "labels_vertical", "Pos.1"]].copy()
        df_vert.columns = ["Profile", "label", "pos"]
    else:
        df_vert = df_ann[["Vertical profile", "labels_vertical", "Pos.1"]].copy()
        df_vert.columns = ["Profile", "label", "pos"]
        df_vert["Profile"] = df_vert["Profile"].ffill()

    df_vert = df_vert.dropna(subset=["label", "pos"]).copy()
    df_vert["pos"] = pd.to_numeric(df_vert["pos"], errors="coerce").astype(int)

    # 3. Parse Strain Profiles and Band Blocks
    # Each strain profile can have one or more distinct Set blocks (label bands)
    if "Profile*" in df_ann.columns and "Set*" in df_ann.columns and not df_ann["Profile*"].dropna().empty:
        df_strain = df_ann[["Profile*", "Set*", "labels_strain", "Pos"]].copy()
        df_strain.columns = ["Profile", "Set", "label", "pos"]
    else:
        df_strain = df_ann[["Strain profile", "Set", "labels_strain", "Pos"]].copy()
        df_strain.columns = ["Profile", "Set", "label", "pos"]
        df_strain["Profile"] = df_strain["Profile"].ffill()
        df_strain["Set"] = df_strain["Set"].ffill()

    df_strain = df_strain.dropna(subset=["label", "pos"]).copy()
    df_strain["pos"] = pd.to_numeric(df_strain["pos"], errors="coerce").astype(int)

    layouts: Dict[str, Dict[str, Any]] = {}
    grouped_assignments = assignments.groupby("annotationSet")

    for ann_set, group in grouped_assignments:
        ann_set_str = str(ann_set).strip()

        # Vertical profile resolution
        vert_group = group[group["Type"].str.lower() == "vertical"]
        if vert_group.empty:
            continue
        vert_profile_name = str(vert_group.iloc[0]["Profile"]).strip()
        vert_rows = df_vert[df_vert["Profile"].astype(str).str.strip() == vert_profile_name].sort_values("pos")

        if vert_rows.empty:
            continue

        vertical_labels = []
        for _, vrow in vert_rows.iterrows():
            val = vrow["label"]
            val_str = str(int(val)) if isinstance(val, (int, float)) and not pd.isna(val) and float(val).is_integer() else str(val).strip()
            vertical_labels.append({
                "pos": int(vrow["pos"]),
                "label": val_str
            })

        grid_rows = max(vl["pos"] for vl in vertical_labels) if vertical_labels else len(vertical_labels)

        # Strain profile(s) and label-band resolution
        strain_groups = group[group["Type"].str.lower() == "strain"].sort_values("Order")

        # Collect raw bands across all assigned strain profiles in order
        raw_bands: List[Dict[str, Any]] = []
        for _, srow in strain_groups.iterrows():
            s_profile_name = str(srow["Profile"]).strip()
            s_profile_df = df_strain[df_strain["Profile"].astype(str).str.strip() == s_profile_name]

            # Group by Set (preserving workbook appearance order)
            # In V10, distinct Set values (A, B, ...) represent separate row bands
            seen_sets = []
            for set_val in s_profile_df["Set"].dropna():
                s_val = str(set_val).strip()
                if s_val not in seen_sets:
                    seen_sets.append(s_val)

            if not seen_sets:
                seen_sets = [None]

            for band_set in seen_sets:
                if band_set is not None:
                    band_df = s_profile_df[s_profile_df["Set"].astype(str).str.strip() == band_set].sort_values("pos")
                else:
                    band_df = s_profile_df.sort_values("pos")

                labels = []
                for _, lrow in band_df.iterrows():
                    lval = lrow["label"]
                    lval_str = str(int(lval)) if isinstance(lval, (int, float)) and not pd.isna(lval) and float(lval).is_integer() else str(lval).strip()
                    labels.append({
                        "pos": int(lrow["pos"]),
                        "label": lval_str
                    })

                if labels:
                    band_name = f"{s_profile_name}:{band_set}" if band_set else s_profile_name
                    raw_bands.append({
                        "profile": band_name,
                        "labels": labels,
                        "max_pos": max(lbl["pos"] for lbl in labels)
                    })

        if not raw_bands:
            continue

        num_bands = len(raw_bands)
        grid_cols = max(rb["max_pos"] for rb in raw_bands)

        # Row band allocation
        strain_bands: List[Dict[str, Any]] = []
        if row_band_overrides and ann_set_str in row_band_overrides:
            overrides = row_band_overrides[ann_set_str]
            if len(overrides) != num_bands:
                raise ValueError(f"Annotation set '{ann_set_str}' has {num_bands} bands but {len(overrides)} row ranges provided in overrides.")
            for idx, rb in enumerate(raw_bands):
                r_start, r_end = overrides[idx]
                strain_bands.append({
                    "order": idx + 1,
                    "profile": rb["profile"],
                    "row_start": int(r_start),
                    "row_end": int(r_end),
                    "labels": rb["labels"]
                })
        else:
            if num_bands == 1:
                strain_bands.append({
                    "order": 1,
                    "profile": raw_bands[0]["profile"],
                    "row_start": 1,
                    "row_end": grid_rows,
                    "labels": raw_bands[0]["labels"]
                })
            else:
                if grid_rows % num_bands != 0:
                    raise ValueError(
                        f"Non-deterministic row allocation for annotation set '{ann_set_str}': "
                        f"{grid_rows} grid rows cannot be evenly divided among {num_bands} strain bands. "
                        f"Please specify explicit row_band_overrides."
                    )
                chunk_size = grid_rows // num_bands
                for idx, rb in enumerate(raw_bands):
                    r_start = idx * chunk_size + 1
                    r_end = (idx + 1) * chunk_size
                    strain_bands.append({
                        "order": idx + 1,
                        "profile": rb["profile"],
                        "row_start": r_start,
                        "row_end": r_end,
                        "labels": rb["labels"]
                    })

        layouts[ann_set_str] = {
            "contract_version": 1,
            "layout_id": ann_set_str,
            "grid_rows": grid_rows,
            "grid_cols": grid_cols,
            "vertical_labels": vertical_labels,
            "strain_bands": strain_bands
        }

    return layouts


_legacy_load_v10 = load_v10
_legacy_extract_layouts = extract_layouts
from .v10_core import build_project_model, extract_layouts


def load_v10(excel_path: str) -> Dict[str, Any]:
    return build_project_model(_legacy_load_v10(excel_path), excel_path)

def derive_plate_layout(
    project_model: Dict[str, Any],
    image_uid: str,
    layouts: Optional[Dict[str, Dict[str, Any]]] = None,
    v10_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Derives the PlateLayout corresponding to a specific image_uid in the ProjectModel.
    """
    if layouts is None:
        layouts = project_model.get("layouts")
        if layouts is None:
            if v10_path is None:
                raise ValueError("ProjectModel has no embedded layouts and no v10_path was provided.")
            layouts = extract_layouts(v10_path)

    # Find image in project_model
    img_entry = next((img for img in project_model.get("images", []) if img.get("image_uid") == image_uid), None)
    if img_entry is None:
        raise KeyError(f"Image UID '{image_uid}' not found in ProjectModel.")

    ann_set = img_entry.get("annotation_set")
    if not ann_set or ann_set not in layouts:
        raise ValueError(f"Annotation set '{ann_set}' for Image UID '{image_uid}' is not present in extracted layouts.")

    layout = copy.deepcopy(layouts[ann_set])
    image_set = str(img_entry.get("set") or "").strip()
    for band in layout.get("strain_bands", []):
        label_sets = band.get("label_sets") or {}
        if not label_sets:
            continue
        matching_key = next(
            (key for key in label_sets if str(key).casefold() == image_set.casefold()),
            None,
        )
        if matching_key is None and len(label_sets) == 1:
            matching_key = next(iter(label_sets))
        if matching_key is None:
            available = ", ".join(str(key) for key in label_sets)
            raise ValueError(
                f"Image UID {image_uid!r} uses Set {image_set!r}, but strain profile "
                f"{band.get('profile')!r} has multiple variants and none match "
                f"({available})."
            )
        labels = copy.deepcopy(label_sets[matching_key])
        band["labels"] = labels
        band["local_grid_cols"] = max(int(label["pos"]) for label in labels)
        band["resolved_label_set"] = str(matching_key)
    layout["grid_cols"] = max(
        int(band["local_grid_cols"]) for band in layout["strain_bands"]
    )
    layout["resolved_image_set"] = image_set
    return layout


def reconcile_image_files(
    project_model: Dict[str, Any],
    files_by_session: Optional[Dict[str, List[str]]] = None,
    provenance_map: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Reconciles expected images from ProjectModel against physical files using controlled evidence order:
    1. Accepted provenance mapping
    2. Exact Original basename within the connected session folder
    3. Exact Working filename
    4. Controlled derivative of Working filename (e.g. known PROCESSED/ANNOTATED prefix, extension change)
    5. Otherwise flags EXPECTED_NOT_PRESENT, AMBIGUOUS, or UNMAPPED_FILE.
    """
    files_by_session = files_by_session or {}
    provenance_map = provenance_map or {}

    expected_images = project_model.get("images", [])
    reconciled_images: List[Dict[str, Any]] = []

    # Track which physical files are claimed (session_uid -> set of normalized filename strings)
    claimed_files: Dict[str, set] = {suid: set() for suid in files_by_session}

    def normalize_stem(fn: str) -> str:
        # Strip path
        base = os.path.basename(fn)
        # Strip known prefixes
        base_no_prefix = re.sub(r"^(PROCESSED\s+|ANNOTATED\s+)", "", base, flags=re.IGNORECASE)
        # Remove extension
        stem = os.path.splitext(base_no_prefix)[0].strip().lower()
        return stem

    for img in expected_images:
        uid = img["image_uid"]
        suid = img.get("session_uid", "")
        orig_fn = (img.get("original") or "").strip()
        working_fn = (img.get("working_filename") or "").strip()

        session_files = files_by_session.get(suid, [])
        matched_file: Optional[str] = None
        status = "EXPECTED_NOT_PRESENT"
        candidates: List[str] = []

        # 1. Provenance
        if uid in provenance_map:
            matched_file = provenance_map[uid]
            status = "READY"
            candidates = [matched_file]
        else:
            # 2. Exact Original match in session files
            orig_matches = [f for f in session_files if os.path.basename(f).lower() == orig_fn.lower()]
            if len(orig_matches) == 1:
                matched_file = orig_matches[0]
                status = "READY"
                candidates = orig_matches
            elif len(orig_matches) > 1:
                status = "AMBIGUOUS"
                candidates = orig_matches
            else:
                # 3. Exact Working filename match
                if working_fn:
                    wf_matches = [f for f in session_files if os.path.basename(f).lower() == working_fn.lower()]
                    if len(wf_matches) == 1:
                        matched_file = wf_matches[0]
                        status = "READY"
                        candidates = wf_matches
                    elif len(wf_matches) > 1:
                        status = "AMBIGUOUS"
                        candidates = wf_matches
                    else:
                        # 4. Controlled derivative match
                        target_stem = normalize_stem(working_fn)
                        deriv_matches = [f for f in session_files if normalize_stem(f) == target_stem]
                        if len(deriv_matches) == 1:
                            matched_file = deriv_matches[0]
                            status = "READY"
                            candidates = deriv_matches
                        elif len(deriv_matches) > 1:
                            status = "AMBIGUOUS"
                            candidates = deriv_matches

        if matched_file and suid in claimed_files:
            claimed_files[suid].add(matched_file)

        reconciled_images.append({
            "image_uid": uid,
            "session_uid": suid,
            "status": status,
            "matched_file": matched_file,
            "candidates": candidates
        })

    # Identify unmapped files
    unmapped_files: List[Dict[str, str]] = []
    for suid, files in files_by_session.items():
        claimed = claimed_files.get(suid, set())
        for f in files:
            if f not in claimed:
                unmapped_files.append({
                    "session_uid": suid,
                    "file": f
                })

    ready_count = sum(1 for r in reconciled_images if r["status"] == "READY")
    not_present_count = sum(1 for r in reconciled_images if r["status"] == "EXPECTED_NOT_PRESENT")
    ambiguous_count = sum(1 for r in reconciled_images if r["status"] == "AMBIGUOUS")

    return {
        "summary": {
            "total_expected": len(expected_images),
            "ready_count": ready_count,
            "expected_not_present_count": not_present_count,
            "ambiguous_count": ambiguous_count,
            "unmapped_count": len(unmapped_files)
        },
        "images": reconciled_images,
        "unmapped_files": unmapped_files
    }


def project_to_legacy_images_rows(project_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compatibility projection: generates legacy images.csv-shaped records from canonical ProjectModel.
    """
    rows = []
    for img in project_model.get("images", []):
        media = img.get("media") or ""
        cond = img.get("condition") or ""
        if media and cond:
            legacy_type = f"{media} + {cond}"
        elif media:
            legacy_type = media
        elif cond:
            legacy_type = cond
        else:
            legacy_type = "default"

        fn = img.get("working_filename") or img.get("original") or ""
        rows.append({
            "Filename": fn,
            "Experiment": img.get("exp", ""),
            "Set": img.get("set", ""),
            "Media": media,
            "Condition": cond,
            "Type": legacy_type,
            "Rep": img.get("rep", ""),
            "Image UID": img.get("image_uid", ""),
            "sessionUID": img.get("session_uid", "")
        })
    return rows


def project_to_legacy_grid_rows(plate_layout: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compatibility projection: generates legacy grid.csv-shaped records from canonical PlateLayout.
    """
    rows = []
    grid_cols = plate_layout.get("grid_cols", 1)
    for band in plate_layout.get("strain_bands", []):
        order = band.get("order", 1)
        r_start = band.get("row_start", 1)
        r_end = band.get("row_end", 1)
        for lbl in band.get("labels", []):
            rows.append({
                "Column": lbl.get("pos"),
                "Strain": lbl.get("label"),
                "GridCols": grid_cols,
                "BandOrder": order,
                "RowStart": r_start,
                "RowEnd": r_end
            })
    return rows
