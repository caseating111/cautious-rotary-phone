from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
DEFAULT_REPORT = APP_DIR / "last_preflight.txt"
DEFAULT_PENDING_CSV = APP_DIR / "pending_images.csv"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
IMAGE_FIELDS = ["Filename", "Experiment", "Set", "Type"]


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["image_root", "crop_output", "grid_csv", "images_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def discover_sources(root: Path) -> list[Path]:
    if not root.is_dir():
        raise SystemExit(f"Image root not found: {root}")
    files: list[Path] = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        files.extend(
            sorted(
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
        )
    return files


def safe_name(value: str) -> str:
    replacements = {
        "/": "-",
        "\\": "-",
        ":": "-",
        "*": "-",
        "?": "",
        '"': "",
        "<": "(",
        ">": ")",
        "|": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def expected_output_names(meta: dict[str, str], grid_rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in sorted(grid_rows, key=lambda item: int(item["Column"])):
        column = int(row["Column"])
        strain = safe_name(row["Strain"])
        prefix = f"{meta['Experiment']}_{meta['Set']}_{meta['Type']}_{column:02d}"
        names.append(f"{prefix}_Top_{strain}.png")
        names.append(f"{prefix}_Low_{strain}.png")
    return names


def build_report(config: dict) -> tuple[list[str], bool, list[dict[str, str]]]:
    image_root = Path(config["image_root"])
    crop_root = Path(config["crop_output"])
    grid = read_csv(Path(config["grid_csv"]))
    images = read_csv(Path(config["images_csv"]))
    sources = discover_sources(image_root)

    grid_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in grid:
        grid_by_key[(row.get("Experiment", ""), row.get("Set", ""))].append(row)

    metadata_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in images:
        metadata_by_name[row.get("Filename", "")].append(row)

    source_name_counts = Counter(path.name for path in sources)
    source_names = set(source_name_counts)
    csv_names = {row.get("Filename", "") for row in images if row.get("Filename", "")}

    unmapped_sources = [path for path in sources if path.name not in metadata_by_name]
    csv_missing_files = sorted(csv_names - source_names)
    duplicate_source_names = sorted(name for name, count in source_name_counts.items() if count > 1)
    duplicate_csv_names = sorted(name for name, rows in metadata_by_name.items() if name and len(rows) > 1)

    mapped_images = 0
    expected_crops = 0
    existing_crops = 0
    missing_crops = 0
    complete_images = 0
    pending_rows: list[dict[str, str]] = []
    grid_missing: list[str] = []
    output_claims: dict[Path, list[Path]] = defaultdict(list)
    logical_name_claims: dict[str, list[Path]] = defaultdict(list)

    for source in sources:
        metadata_rows = metadata_by_name.get(source.name, [])
        if len(metadata_rows) != 1:
            continue
        meta = metadata_rows[0]
        key = (meta.get("Experiment", ""), meta.get("Set", ""))
        grid_rows = grid_by_key.get(key, [])
        if not grid_rows:
            grid_missing.append(f"{source.name}: {key[0]}/{key[1]}")
            continue

        mapped_images += 1
        names = expected_output_names(meta, grid_rows)
        expected_crops += len(names)
        output_dir = crop_root / source.parent.name
        image_missing = 0
        for name in names:
            output_path = output_dir / name
            output_claims[output_path].append(source)
            logical_name_claims[name.lower()].append(source)
            if output_path.is_file():
                existing_crops += 1
            else:
                missing_crops += 1
                image_missing += 1

        if image_missing:
            pending_rows.append({field: meta.get(field, "") for field in IMAGE_FIELDS})
        else:
            complete_images += 1

    output_collisions = []
    for output_path, claimants in sorted(output_claims.items(), key=lambda item: str(item[0])):
        unique_claimants = sorted({path.relative_to(image_root) for path in claimants}, key=str)
        if len(unique_claimants) > 1:
            rel_output = output_path.relative_to(crop_root)
            sources_text = ", ".join(str(path) for path in unique_claimants)
            output_collisions.append(f"{rel_output} <- {sources_text}")

    downstream_ambiguities = []
    for name, claimants in sorted(logical_name_claims.items()):
        unique_claimants = sorted({path.relative_to(image_root) for path in claimants}, key=str)
        if len(unique_claimants) > 1:
            folders = {path.parent for path in unique_claimants}
            if len(folders) > 1:
                sources_text = ", ".join(str(path) for path in unique_claimants)
                downstream_ambiguities.append(f"{name} <- {sources_text}")

    lines = [
        "BATCH PREFLIGHT",
        f"Source folders: {len([p for p in image_root.iterdir() if p.is_dir()])}",
        f"Source images discovered: {len(sources)}",
        f"Mapped source images ready: {mapped_images}",
        f"Already complete images: {complete_images}",
        f"Images still requiring batch work: {len(pending_rows)}",
        f"Expected crops for ready images: {expected_crops}",
        f"Existing expected crops: {existing_crops}",
        f"Crops still to produce: {missing_crops}",
    ]

    sections = [
        ("UNMAPPED SOURCE IMAGES", [str(path.relative_to(image_root)) for path in unmapped_sources]),
        ("CSV ROWS WITH NO DISCOVERED SOURCE FILE", csv_missing_files),
        ("DUPLICATE SOURCE BASENAMES", duplicate_source_names),
        ("DUPLICATE images.csv FILENAMES", duplicate_csv_names),
        ("MAPPED IMAGES WITH NO GRID DEFINITION", sorted(set(grid_missing))),
        ("OUTPUT FILENAME COLLISIONS", output_collisions),
        ("DOWNSTREAM CROP-NAME AMBIGUITIES", downstream_ambiguities),
    ]

    problems = False
    for title, items in sections:
        if not items:
            continue
        problems = True
        lines.extend(["", f"{title} ({len(items)})"])
        lines.extend(f"- {item}" for item in items)

    lines.extend(["", "STATUS: CHECK ITEMS ABOVE BEFORE BATCH ALIGNMENT" if problems else "STATUS: READY FOR BATCH ALIGNMENT"])
    return lines, problems, pending_rows


def write_pending_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=IMAGE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--pending-images-csv", type=Path, default=DEFAULT_PENDING_CSV)
    args = parser.parse_args()

    lines, problems, pending_rows = build_report(load_config(args.config))
    text = "\n".join(lines) + "\n"
    print(text, end="")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
    write_pending_csv(args.pending_images_csv, pending_rows)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
