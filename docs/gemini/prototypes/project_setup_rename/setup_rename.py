import os
import shutil
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import sys

# Ensure v10 adapter is importable
v10_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "v10"))
if v10_dir not in sys.path:
    sys.path.insert(0, v10_dir)

from adapter import load_v10, reconcile_image_files


def initialize_project_tree(project_root: str, create_subdirs: bool = True) -> Dict[str, str]:
    """
    Initializes standard project directory tree structure:
    - raw/
    - working/
    - processed/
    - annotated/
    - crops/unprocessed/
    - crops/processed/
    - matrices/
    - state/
    """
    dirs = {
        "raw": os.path.join(project_root, "raw"),
        "working": os.path.join(project_root, "working"),
        "processed": os.path.join(project_root, "processed"),
        "annotated": os.path.join(project_root, "annotated"),
        "crops_unprocessed": os.path.join(project_root, "crops", "unprocessed"),
        "crops_processed": os.path.join(project_root, "crops", "processed"),
        "matrices": os.path.join(project_root, "matrices"),
        "state": os.path.join(project_root, "state"),
    }
    if create_subdirs:
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)
    return dirs


def generate_conversion_map_text(
    project_model: Dict[str, Any],
    rename_results: List[Dict[str, Any]],
    project_root: Optional[str] = None
) -> str:
    """
    Generates a clear human-readable audit text file mapping:
    raw relative path -> working relative path [UID: ...] [Status: ...]
    Grouped by Experiment and Set with clean dividers.
    """
    res_by_uid = {r["image_uid"]: r for r in rename_results}
    images = project_model.get("images", [])

    lines = [
        "================================================================================",
        "                     V10 IMAGE NAME CONVERSION & AUDIT MAP                      ",
        "================================================================================",
        "This file records the mapping from raw source camera files to V10 working files.",
        "Canonical identity is preserved via Image UID across all processing stages.",
        "",
    ]

    # Group images by Exp, then Set
    exp_groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for img in images:
        exp = img.get("exp") or "Unknown"
        img_set = img.get("set") or "Default"
        if exp not in exp_groups:
            exp_groups[exp] = {}
        if img_set not in exp_groups[exp]:
            exp_groups[exp][img_set] = []
        exp_groups[exp][img_set].append(img)

    for exp in sorted(exp_groups.keys()):
        lines.append(f"==================== Experiment {exp} ====================")
        lines.append("")
        set_dict = exp_groups[exp]
        for s_name in sorted(set_dict.keys()):
            lines.append(f"  -------------------- Set {s_name} --------------------")
            for img in set_dict[s_name]:
                uid = img["image_uid"]
                r = res_by_uid.get(uid, {})
                disposition = r.get("disposition", "UNKNOWN")
                raw_p = r.get("raw_path") or img.get("original") or "N/A"
                work_p = r.get("working_path") or img.get("working_filename") or "N/A"
                
                if project_root:
                    if os.path.isabs(raw_p) and raw_p.startswith(project_root):
                        raw_p = os.path.relpath(raw_p, project_root)
                    if os.path.isabs(work_p) and work_p.startswith(project_root):
                        work_p = os.path.relpath(work_p, project_root)
                
                lines.append(f"    {raw_p} -> {work_p}")
                lines.append(f"        [UID: {uid}]  [Session: {img.get('session_uid')}]  [Status: {disposition}]")
            lines.append("")
        lines.append("")

    return "\n".join(lines)


def prepare_working_copy(
    project_model: Dict[str, Any],
    project_root: str,
    raw_root: Optional[str] = None,
    working_root: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Prepares the project directory tree and creates/maps working copies of raw images.
    
    Options:
    - enable_rename: bool (default True). If True, copy to V10 working_filename. If False, copy preserving original name.
    - preview_only: bool (default False). If True, compute dispositions without filesystem writes.
    - write_conversion_map: bool (default True). Write image_name_conversions.txt at project_root.
    - collision_policy: "error" | "disambiguate_with_uid" (default "error").
    - provenance_map: Optional dict mapping image_uid -> accepted physical file.
    - custom_session_folders: Optional dict mapping session_uid -> folder path.
    """
    options = options or {}
    enable_rename = options.get("enable_rename", True)
    preview_only = options.get("preview_only", False)
    write_conversion_map = options.get("write_conversion_map", True)
    collision_policy = options.get("collision_policy", "error")
    provenance_map = options.get("provenance_map", {})
    custom_session_folders = options.get("custom_session_folders", {})

    raw_root = os.path.abspath(raw_root or os.path.join(project_root, "raw"))
    working_root = os.path.abspath(working_root or os.path.join(project_root, "working"))
    project_root = os.path.abspath(project_root)

    # 1. Initialize project directories (unless preview)
    if not preview_only:
        initialize_project_tree(project_root, create_subdirs=True)
        os.makedirs(raw_root, exist_ok=True)
        os.makedirs(working_root, exist_ok=True)

    # 2. Scan raw root for physical files per session
    files_by_session: Dict[str, List[str]] = {}
    sessions = project_model.get("sessions", [])
    for s in sessions:
        suid = s["session_uid"]
        session_folder = custom_session_folders.get(suid, os.path.join(raw_root, suid))
        found_files = []
        if os.path.exists(session_folder) and os.path.isdir(session_folder):
            for entry in os.scandir(session_folder):
                if entry.is_file():
                    found_files.append(entry.path)
        elif os.path.exists(raw_root) and os.path.isdir(raw_root):
            for entry in os.scandir(raw_root):
                if entry.is_file():
                    found_files.append(entry.path)
        files_by_session[suid] = found_files

    # 3. Reconcile expected images with physical files
    rec_result = reconcile_image_files(
        project_model,
        files_by_session=files_by_session,
        provenance_map=provenance_map
    )

    reconciled_lookup = {r["image_uid"]: r for r in rec_result.get("images", [])}

    # 4. Plan destination working paths and check for target collisions
    dest_path_to_uid: Dict[str, str] = {}
    image_plans: List[Dict[str, Any]] = []

    for img in project_model.get("images", []):
        uid = img["image_uid"]
        suid = img.get("session_uid", "")
        rec = reconciled_lookup.get(uid, {})
        status = rec.get("status", "EXPECTED_NOT_PRESENT")
        matched_raw_file = rec.get("matched_file")

        if enable_rename:
            target_fn = img.get("working_filename") or img.get("original") or f"{uid}.jpg"
        else:
            target_fn = img.get("original") or (os.path.basename(matched_raw_file) if matched_raw_file else f"{uid}.jpg")

        target_rel_path = os.path.join("working", target_fn)
        target_abs_path = os.path.join(working_root, target_fn)
        target_key = target_abs_path.lower()

        disposition = "SKIPPED"
        disposition_detail = ""

        if target_key in dest_path_to_uid and dest_path_to_uid[target_key] != uid:
            if collision_policy == "disambiguate_with_uid":
                stem, ext = os.path.splitext(target_fn)
                disambig_fn = f"{stem}_{uid}{ext}"
                target_rel_path = os.path.join("working", disambig_fn)
                target_abs_path = os.path.join(working_root, disambig_fn)
                target_key = target_abs_path.lower()
                dest_path_to_uid[target_key] = uid
            else:
                disposition = "TARGET_COLLISION"
                disposition_detail = f'Destination path "{target_fn}" collides with Image UID "{dest_path_to_uid[target_key]}"'
        else:
            dest_path_to_uid[target_key] = uid

        if disposition != "TARGET_COLLISION":
            if status == "READY" and matched_raw_file:
                if os.path.exists(target_abs_path):
                    try:
                        raw_size = os.path.getsize(matched_raw_file)
                        target_size = os.path.getsize(target_abs_path)
                        if raw_size == target_size:
                            disposition = "UNCHANGED_CURRENT"
                            disposition_detail = "Target file already exists with matching size"
                        else:
                            disposition = "COPIED_RENAMED" if enable_rename else "COPIED_ORIGINAL_NAME"
                            disposition_detail = "Target file exists but size differs; will update"
                    except OSError:
                        disposition = "COPIED_RENAMED" if enable_rename else "COPIED_ORIGINAL_NAME"
                        disposition_detail = "Will copy to working directory"
                else:
                    disposition = "COPIED_RENAMED" if enable_rename else "COPIED_ORIGINAL_NAME"
                    disposition_detail = "Will copy to working directory"
            elif status == "EXPECTED_NOT_PRESENT":
                disposition = "EXPECTED_NOT_PRESENT"
                disposition_detail = "Expected by V10 model but no physical raw file found"
            elif status == "AMBIGUOUS":
                disposition = "AMBIGUOUS_SOURCE"
                disposition_detail = f"Multiple matching raw files found: {rec.get('candidates')}"

        raw_rel = os.path.relpath(matched_raw_file, project_root) if (matched_raw_file and os.path.isabs(matched_raw_file) and matched_raw_file.startswith(project_root)) else (matched_raw_file or os.path.join("raw", suid, img.get("original", "")))

        image_plans.append({
            "image_uid": uid,
            "session_uid": suid,
            "raw_path": raw_rel,
            "working_path": target_rel_path,
            "raw_abs_path": matched_raw_file,
            "working_abs_path": target_abs_path,
            "disposition": disposition,
            "disposition_detail": disposition_detail
        })

    # 5. Execute file copies if not preview
    if not preview_only:
        for plan in image_plans:
            disp = plan["disposition"]
            if disp in ("COPIED_RENAMED", "COPIED_ORIGINAL_NAME"):
                src = plan["raw_abs_path"]
                dst = plan["working_abs_path"]
                if src and os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

    # 6. Generate conversion map text
    conv_map_text = generate_conversion_map_text(project_model, image_plans, project_root=project_root)
    conv_map_path = os.path.join(project_root, "image_name_conversions.txt")
    if write_conversion_map and not preview_only:
        with open(conv_map_path, "w", encoding="utf-8") as f:
            f.write(conv_map_text)

    copied_renamed = sum(1 for p in image_plans if p["disposition"] == "COPIED_RENAMED")
    copied_orig = sum(1 for p in image_plans if p["disposition"] == "COPIED_ORIGINAL_NAME")
    unchanged = sum(1 for p in image_plans if p["disposition"] == "UNCHANGED_CURRENT")
    not_present = sum(1 for p in image_plans if p["disposition"] == "EXPECTED_NOT_PRESENT")
    ambiguous = sum(1 for p in image_plans if p["disposition"] == "AMBIGUOUS_SOURCE")
    collision = sum(1 for p in image_plans if p["disposition"] == "TARGET_COLLISION")
    skipped = sum(1 for p in image_plans if p["disposition"] == "SKIPPED")

    clean_images = []
    for p in image_plans:
        clean_images.append({
            "image_uid": p["image_uid"],
            "session_uid": p["session_uid"],
            "raw_path": p["raw_path"],
            "working_path": p["working_path"],
            "disposition": p["disposition"],
            "disposition_detail": p["disposition_detail"]
        })

    return {
        "contract_version": 1,
        "project_root": project_root,
        "raw_root": raw_root,
        "working_root": working_root,
        "conversion_map_path": os.path.relpath(conv_map_path, project_root) if os.path.exists(conv_map_path) or preview_only else conv_map_path,
        "conversion_map_text": conv_map_text,
        "summary": {
            "total_expected": len(image_plans),
            "copied_renamed_count": copied_renamed,
            "copied_original_count": copied_orig,
            "unchanged_current_count": unchanged,
            "expected_not_present_count": not_present,
            "ambiguous_source_count": ambiguous,
            "target_collision_count": collision,
            "skipped_count": skipped
        },
        "images": clean_images,
        "unmapped_files": rec_result.get("unmapped_files", [])
    }
