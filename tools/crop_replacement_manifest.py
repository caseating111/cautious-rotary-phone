"""Prepare an exact, no-side-effect crop replacement manifest for Fiji."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

try:
    from tools import preflight_batch
except ModuleNotFoundError:
    import preflight_batch


def write_manifest(config: dict, row: dict[str, str], path: Path) -> int:
    crop_root = Path(config["crop_output"])
    sources = {item.name.casefold(): item for item in preflight_batch.discover_sources(Path(config["image_root"]))}
    source = sources.get(row["Filename"].casefold())
    if source is None:
        raise SystemExit(f"Selected source is not under image_root: {row['Filename']}")
    grid = [item for item in preflight_batch.read_csv(Path(config["grid_csv"])) if item["Experiment"] == row["Experiment"] and item["Set"] == row["Set"]]
    if not grid:
        raise SystemExit(f"No grid rows found for {row['Experiment']}/{row['Set']}.")
    by_strain: dict[str, list[Path]] = defaultdict(list)
    for item in grid:
        strain = preflight_batch.safe_name(item["Strain"])
        prefix = f"{row['Experiment']}_{row['Set']}_{row['Type']}_{int(item['Column']):02d}"
        for state in ("Top", "Low"):
            crop = crop_root / source.parent.name / f"{prefix}_{state}_{strain}.png"
            if crop.is_file():
                by_strain[strain].append(crop)
    planned_files: list[tuple[str, str, str, Path]] = []
    for strain, files in sorted(by_strain.items()):
        stamp = datetime.fromtimestamp(median(item.stat().st_ctime for item in files)).strftime("%d.%m.%y_%H.%M")
        for crop in files:
            planned_files.append((strain, strain, stamp, crop))

    batch_root = crop_root.parent / "Discards" / "Discarded_Crops" / f"{row['Experiment']}_{row['Set']}"
    batch_number = 1
    while True:
        batch_dir = batch_root / f"DiscardBatch_{batch_number:03d}"
        targets = [batch_dir / group / crop.name for group, _strain, _stamp, crop in planned_files]
        if not any(target.exists() for target in targets):
            break
        batch_number += 1

    prepared_at = datetime.now().strftime("%d.%m.%y_%H.%M")
    planned: list[dict[str, str]] = []
    archive_manifest = batch_dir / "discard_manifest.tsv"
    for group, strain, original_stamp, crop in planned_files:
        target = batch_dir / group / crop.name
        planned.append(
            {
                "folder": source.parent.name,
                "filename": row["Filename"],
                "source": crop.as_posix(),
                "target": target.as_posix(),
                "strain": strain,
                "original_crop_time": original_stamp,
                "archive_manifest": archive_manifest.as_posix(),
                "archived_at": prepared_at,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "folder",
                "filename",
                "source",
                "target",
                "strain",
                "original_crop_time",
                "archive_manifest",
                "archived_at",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(planned)
    return len(planned)

def write_manifests(config: dict, rows: list[dict[str, str]], path: Path) -> int:
    """Combine exact per-plate replacement plans without target collisions."""
    planned: list[dict[str, str]] = []
    reserved_targets: set[Path] = set()
    for row in rows:
        write_manifest(config, row, path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            entries = list(csv.DictReader(handle, delimiter="\t"))
        for entry in entries:
            target = Path(entry["target"])
            batch_dir = target.parents[1]
            number = 1
            while target.exists() or target in reserved_targets:
                number += 1
                new_batch = batch_dir.parent / f"DiscardBatch_{number:03d}"
                target = new_batch / target.parent.name / target.name
            if target != Path(entry["target"]):
                entry["target"] = target.as_posix()
                entry["archive_manifest"] = (target.parents[1] / "discard_manifest.tsv").as_posix()
            reserved_targets.add(target)
            planned.append(entry)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(planned[0]) if planned else ["folder", "filename", "source", "target", "strain", "original_crop_time", "archive_manifest", "archived_at"], delimiter="\t")
        writer.writeheader()
        writer.writerows(planned)
    return len(planned)
