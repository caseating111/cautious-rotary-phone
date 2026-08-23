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
    planned: list[dict[str, str]] = []
    for strain, files in sorted(by_strain.items()):
        stamp = datetime.fromtimestamp(median(item.stat().st_ctime for item in files)).strftime("%d.%m.%y_%H.%M")
        target_dir = crop_root.parent / "Discards" / "Discarded_Crops" / f"{row['Experiment']}_{row['Set']}" / f"{stamp}_{strain}"
        for crop in files:
            target = target_dir / crop.name
            if target.exists():
                raise SystemExit(f"Refusing to overwrite an archived crop: {target}")
            planned.append(
                {
                    "folder": source.parent.name,
                    "filename": row["Filename"],
                    "source": crop.as_posix(),
                    "target": target.as_posix(),
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["folder", "filename", "source", "target"], delimiter="\t")
        writer.writeheader()
        writer.writerows(planned)
    return len(planned)
