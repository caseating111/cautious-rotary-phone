from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from tools.applets.v10_adapter import (
    derive_plate_layout,
    project_to_legacy_images_rows,
)
from tools.project_dates import working_filename_for
from tools.project_paths import canonical_path

CSV_NAMES = (
    "grid.csv",
    "images.csv",
    "condition_order.csv",
    "v10_master_registry.csv",
    "v10_plate_layout.csv",
)


def _csv_text(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _session_map(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("session_uid") or ""): item
        for item in model.get("sessions", [])
    }


def _images_rows(model: dict[str, Any], filename_date_style: str) -> list[dict[str, Any]]:
    sessions = _session_map(model)
    projected = {row["Image UID"]: row for row in project_to_legacy_images_rows(model)}
    rows: list[dict[str, Any]] = []
    for image in model.get("images", []):
        uid = str(image.get("image_uid") or "")
        row = projected[uid]
        filename = working_filename_for(
            image,
            sessions.get(str(image.get("session_uid") or ""), {}),
            date_style=filename_date_style,
        )
        rows.append(
            {
                "Filename": filename,
                "Experiment": row["Experiment"],
                "Set": row["Set"],
                "Type": row["Type"],
            }
        )
    return rows


def _master_registry_rows(
    model: dict[str, Any], filename_date_style: str
) -> list[dict[str, Any]]:
    sessions = _session_map(model)
    rows: list[dict[str, Any]] = []
    for image in model.get("images", []):
        session = sessions.get(str(image.get("session_uid") or ""), {})
        rows.append(
            {
                "Exp": image.get("exp", session.get("exp", "")),
                "ID": image.get("id", ""),
                "sessionUID*": image.get("session_uid", ""),
                "Image #": image.get("image_number", ""),
                "Sample description": image.get("sample_description", ""),
                "Set": image.get("set", ""),
                "Media": image.get("media", ""),
                "Condition": image.get("condition", ""),
                "Rep #": image.get("rep", ""),
                "Original": image.get("original", ""),
                "Image UID": image.get("image_uid", ""),
                "Working filename": working_filename_for(
                    image, session, date_style=filename_date_style
                ),
                "Arrangement": image.get("arrangement", ""),
                "annotationSet": image.get("annotation_set", ""),
                "Date": image.get(
                    "date_display", session.get("date_display", "")
                ),
                "Date*": image.get("date", session.get("date", "")),
                "Time": image.get("time", session.get("time", "")),
                "figureDescriptionLabel": image.get(
                    "figure_description_label", ""
                ),
                "Filename status": image.get("filename_status", ""),
                "Base filename*": image.get("base_filename", ""),
                "Base count*": image.get("base_count", ""),
                "Set filename*": image.get("set_filename", ""),
                "Set filename count*": image.get("set_filename_count", ""),
            }
        )
    return rows


def _plate_layout_rows(model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for layout_id, raw_layout in sorted(model.get("layouts", {}).items()):
        vertical = {
            int(label["pos"]): str(label["label"])
            for label in raw_layout.get("vertical_labels", [])
        }
        variant_names = list(
            dict.fromkeys(
                str(name)
                for band in raw_layout.get("strain_bands", [])
                for name in (band.get("label_sets") or {})
            )
        ) or [""]
        for variant_name in variant_names:
            selected_bands: list[
                tuple[dict[str, Any], list[dict[str, Any]], str]
            ] = []
            for band in raw_layout.get("strain_bands", []):
                label_sets = band.get("label_sets") or {}
                matching = next(
                    (
                        name
                        for name in label_sets
                        if str(name).casefold() == variant_name.casefold()
                    ),
                    None,
                )
                if matching is None and len(label_sets) == 1:
                    matching = next(iter(label_sets))
                labels = (
                    label_sets[matching]
                    if matching is not None
                    else band.get("labels", [])
                )
                selected_bands.append((band, labels, str(matching or "")))
            grid_cols = max(
                int(label["pos"])
                for _band, labels, _selected in selected_bands
                for label in labels
            )
            for band, labels, selected_name in selected_bands:
                for label in labels:
                    rows.append(
                        {
                            "annotationSet": layout_id,
                            "Set": selected_name or variant_name,
                            "GridRows": raw_layout.get("grid_rows", ""),
                            "GridCols": grid_cols,
                            "BandOrder": band.get("order", ""),
                            "Profile": band.get("profile", ""),
                            "RowStart": band.get("row_start", ""),
                            "RowEnd": band.get("row_end", ""),
                            "Column": label.get("pos", ""),
                            "Strain": label.get("label", ""),
                            "VerticalLabels": " | ".join(
                                f"{position}:{text}"
                                for position, text in sorted(vertical.items())
                            ),
                        }
                    )
    return rows


def _layout_columns(layout: dict[str, Any]) -> list[tuple[int, str]]:
    by_position: dict[int, set[str]] = {}
    for band in layout.get("strain_bands", []):
        for label in band.get("labels", []):
            position = int(label["pos"])
            by_position.setdefault(position, set()).add(str(label["label"]))
    conflicts = {position: labels for position, labels in by_position.items() if len(labels) > 1}
    if conflicts:
        details = ", ".join(
            f"column {position}: {sorted(labels)}" for position, labels in sorted(conflicts.items())
        )
        raise ValueError(
            "This V10 PlateLayout has different strain labels in row bands and cannot be flattened safely to legacy grid.csv ("
            + details
            + "). Use the V10 applets or keep the current pinned CSV snapshot."
        )
    if not by_position:
        raise ValueError("V10 PlateLayout contains no strain labels for grid.csv.")
    maximum = max(by_position)
    if sorted(by_position) != list(range(1, maximum + 1)):
        raise ValueError("V10 strain positions must be contiguous before grid.csv export.")
    return [(position, next(iter(by_position[position]))) for position in range(1, maximum + 1)]


def _grid_rows(model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for image in model.get("images", []):
        layout_id = str(image.get("annotation_set") or "")
        try:
            layout = derive_plate_layout(model, str(image["image_uid"]))
        except ValueError:
            # Preserve the full V10 model/snapshots while omitting only image
            # groups that cannot be represented by the five-column legacy
            # grid projection.
            continue
        exp, set_name = str(image.get("exp") or ""), str(image.get("set") or "")
        identity = (exp.casefold(), set_name.casefold(), layout_id.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        columns = _layout_columns(layout)
        for position, label in columns:
            rows.append(
                {
                    "Experiment": exp,
                    "Set": set_name,
                    "GridCols": len(columns),
                    "Column": position,
                    "Strain": label,
                }
            )
    if not rows:
        raise ValueError(
            "No V10 image group can be represented safely as legacy grid.csv."
        )
    return rows


def build_csv_payload(
    model: dict[str, Any],
    *,
    filename_date_style: str = "v10",
) -> dict[str, str]:
    images = _images_rows(model, filename_date_style)
    try:
        grid = _grid_rows(model)
    except ValueError:
        grid = None
    master = _master_registry_rows(model, filename_date_style)
    plate_layout = _plate_layout_rows(model)
    conditions: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for row in images:
        type_name = str(row["Type"])
        identity = type_name.casefold()
        if identity not in seen_types:
            seen_types.add(identity)
            conditions.append({"Order": len(conditions) + 1, "Type": type_name})
    payload = {
        "images.csv": _csv_text(
            ["Filename", "Experiment", "Set", "Type"], images
        ),
        "condition_order.csv": _csv_text(["Order", "Type"], conditions),
        "v10_master_registry.csv": _csv_text(
            [
                "Exp", "ID", "sessionUID*", "Image #", "Sample description",
                "Set", "Media", "Condition", "Rep #", "Original", "Image UID",
                "Working filename", "Arrangement", "annotationSet", "Date", "Date*",
                "Time", "figureDescriptionLabel", "Filename status",
                "Base filename*", "Base count*", "Set filename*",
                "Set filename count*",
            ],
            master,
        ),
        "v10_plate_layout.csv": _csv_text(
            [
                "annotationSet", "Set", "GridRows", "GridCols", "BandOrder",
                "Profile", "RowStart", "RowEnd", "Column", "Strain",
                "VerticalLabels",
            ],
            plate_layout,
        ),
    }
    if grid is not None:
        payload["grid.csv"] = _csv_text(
            ["Experiment", "Set", "GridCols", "Column", "Strain"], grid
        )
    return payload


def _payload_hash(payload: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(payload):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload[name].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _read_current(metadata: Path) -> dict[str, Any] | None:
    pointer = metadata / "CSV Snapshots" / "current.json"
    if not pointer.is_file():
        return None
    try:
        value = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read current CSV snapshot: {exc}") from exc
    return value


def compare_csv_snapshot(
    model: dict[str, Any],
    project_root: str | Path,
    *,
    filename_date_style: str = "v10",
) -> dict[str, Any]:
    metadata = canonical_path(project_root, "metadata")
    payload = build_csv_payload(model, filename_date_style=filename_date_style)
    digest = _payload_hash(payload)
    current = _read_current(metadata)
    return {
        "status": "UNCHANGED" if current and current.get("payload_sha256") == digest else "CHANGED",
        "payload_sha256": digest,
        "current": current,
        "files": sorted(payload),
        "legacy_grid_available": "grid.csv" in payload,
    }


def write_csv_snapshot(
    model: dict[str, Any],
    project_root: str | Path,
    *,
    filename_date_style: str = "v10",
    pinned: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    metadata = canonical_path(root, "metadata")
    snapshots = metadata / "CSV Snapshots"
    current = _read_current(metadata)
    if pinned and current:
        return {**current, "status": "PINNED_CURRENT", "pinned": True}
    payload = build_csv_payload(model, filename_date_style=filename_date_style)
    digest = _payload_hash(payload)
    if current and current.get("payload_sha256") == digest:
        return {**current, "status": "UNCHANGED_CURRENT", "pinned": pinned}
    existing = [
        int(path.name)
        for path in snapshots.iterdir()
        if path.is_dir() and path.name.isdigit()
    ] if snapshots.is_dir() else []
    number = max(existing, default=0) + 1
    snapshot_id = f"{number:03d}"
    metadata.mkdir(parents=True, exist_ok=True)
    snapshots.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".csv-snapshot-", dir=snapshots))
    destination = snapshots / snapshot_id
    try:
        for name, text in payload.items():
            (temporary / name).write_text(text, encoding="utf-8", newline="")
        manifest = {
            "snapshot_id": snapshot_id,
            "payload_sha256": digest,
            "filename_date_style": filename_date_style,
            "pinned": pinned,
            "files": sorted(payload),
            "legacy_grid_available": "grid.csv" in payload,
        }
        (temporary / "snapshot.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, destination)
        previous_files = set(current.get("files", [])) if current else set()
        for name in previous_files.difference(payload):
            if name in CSV_NAMES:
                stale = metadata / name
                if stale.is_file():
                    stale.unlink()
        for name in payload:
            source = destination / name
            target = metadata / name
            staged = target.with_suffix(target.suffix + ".tmp")
            shutil.copy2(source, staged)
            os.replace(staged, target)
        pointer = snapshots / "current.json"
        staged_pointer = pointer.with_suffix(".json.tmp")
        staged_pointer.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staged_pointer, pointer)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {**manifest, "status": "CREATED", "directory": str(destination)}
