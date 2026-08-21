from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
DEFAULT_REPORT = APP_DIR / "last_preflight.txt"
DEFAULT_PENDING_CSV = APP_DIR / "pending_images.csv"
REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "tools" / "validate_project_csvs.py"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
IMAGE_FIELDS = ["Filename", "Experiment", "Set", "Type"]


def validate_output_layout(image_root: str | Path, crop_output: str | Path) -> None:
    source_root = Path(image_root).resolve()
    crop_root = Path(crop_output).resolve()
    if crop_root == source_root or crop_root.is_relative_to(source_root):
        raise SystemExit(
            "crop_output must be outside image_root. Derived crop files should not be written into the production source-image tree."
        )


def load_config(path: Path, require_fiji_handoff_paths: bool = True) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["image_root", "crop_output", "grid_csv", "images_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    validate_output_layout(data["image_root"], data["crop_output"])
    if require_fiji_handoff_paths:
        for key in ("grid_csv", "crop_output"):
            if ";" in str(data[key]):
                raise SystemExit(
                    f"Configured {key} contains a semicolon, which conflicts with the composed Fiji macro-argument delimiter: {data[key]}"
                )
    try:
        data["crop_width"] = int(data.get("crop_width", 130))
        data["crop_height"] = int(data.get("crop_height", 546))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid crop dimensions: {exc}") from exc
    if data["crop_width"] <= 0 or data["crop_height"] <= 0:
        raise SystemExit("Crop dimensions must be positive.")
    return data


def validate_project_csvs(config: dict) -> None:
    if not VALIDATOR.is_file():
        raise SystemExit(f"CSV validator not found: {VALIDATOR}")
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            str(config["grid_csv"]),
            str(config["images_csv"]),
            str(config["condition_order_csv"]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        raise SystemExit(output or "CSV validation failed before batch preflight.")


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


def expected_crop_issue(path: Path, source_mtime: int, crop_width: int, crop_height: int) -> str | None:
    if not path.is_file():
        return "missing"
    if path.stat().st_mtime_ns < source_mtime:
        return "older than source"
    try:
        with Image.open(path) as image:
            size = image.size
    except OSError:
        return "unreadable/corrupt image"

    valid_sizes = {(crop_width, crop_height), (crop_height, crop_width)}
    if size not in valid_sizes:
        return f"size {size[0]}x{size[1]} does not match configured {crop_width}x{crop_height} (or rotated)"
    return None


def build_report(
    config: dict,
    require_full_column_geometry: bool = True,
    require_fiji_handoff_paths: bool = True,
) -> tuple[list[str], bool, list[dict[str, str]]]:
    image_root = Path(config["image_root"])
    crop_root = Path(config["crop_output"])
    validate_output_layout(image_root, crop_root)
    crop_width = int(config.get("crop_width", 130))
    crop_height = int(config.get("crop_height", 546))
    grid = read_csv(Path(config["grid_csv"]))
    images = read_csv(Path(config["images_csv"]))
    sources = discover_sources(image_root)

    source_folders = sorted(path for path in image_root.iterdir() if path.is_dir())
    delimiter_unsafe_folders = []
    if require_fiji_handoff_paths:
        delimiter_unsafe_folders = [path.name for path in source_folders if ";" in path.name]

    grid_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in grid:
        grid_by_key[(row.get("Experiment", ""), row.get("Set", ""))].append(row)

    unsupported_full_column_grids: list[str] = []
    if require_full_column_geometry:
        for (exp, set_name), rows_for_grid in sorted(grid_by_key.items()):
            declared_values = {int(row["GridCols"]) for row in rows_for_grid}
            if len(declared_values) == 1:
                declared = next(iter(declared_values))
                if declared < 2:
                    unsupported_full_column_grids.append(f"{exp}/{set_name}: GridCols={declared}")

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
    partial_images: list[str] = []
    stale_expected_crops: list[str] = []
    incompatible_expected_crops: list[str] = []
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
        image_existing = 0
        source_mtime = source.stat().st_mtime_ns
        for name in names:
            output_path = output_dir / name
            output_claims[output_path].append(source)
            logical_name_claims[name.lower()].append(source)
            issue = expected_crop_issue(output_path, source_mtime, crop_width, crop_height)
            if issue is None:
                existing_crops += 1
                image_existing += 1
            else:
                if output_path.is_file():
                    detail = f"{output_path.relative_to(crop_root)} <- {issue}"
                    if issue == "older than source":
                        stale_expected_crops.append(detail + f": {source.relative_to(image_root)}")
                    else:
                        incompatible_expected_crops.append(detail)
                missing_crops += 1
                image_missing += 1

        if image_missing:
            pending_rows.append({field: meta.get(field, "") for field in IMAGE_FIELDS})
            if image_existing:
                partial_images.append(
                    f"{source.relative_to(image_root)}: {image_existing} current, {image_missing} missing/stale/incompatible"
                )
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

    expected_paths = {path.resolve() for path in output_claims}
    unexpected_crop_pngs: list[str] = []
    if crop_root.is_dir():
        for path in sorted(crop_root.rglob("*.png")):
            if path.is_file() and path.resolve() not in expected_paths:
                unexpected_crop_pngs.append(str(path.relative_to(crop_root)))

    lines = [
        "BATCH PREFLIGHT",
        f"Source folders: {len(source_folders)}",
        f"Source images discovered: {len(sources)}",
        f"Mapped source images ready: {mapped_images}",
        f"Already complete images: {complete_images}",
        f"Images still requiring batch work: {len(pending_rows)}",
        f"Expected crops for ready images: {expected_crops}",
        f"Current expected crops: {existing_crops}",
        f"Crops still to produce/rebuild: {missing_crops}",
    ]

    sections = [
        ("GRIDS UNSUPPORTED BY FULL-COLUMN ALIGNMENT", unsupported_full_column_grids),
        ("SOURCE FOLDERS UNSAFE FOR FIJI ARGUMENT HANDOFF", delimiter_unsafe_folders),
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

    if stale_expected_crops:
        lines.extend(["", f"STALE EXPECTED CROPS — WILL REBUILD ({len(stale_expected_crops)})"])
        lines.append(
            "These derived crops are older than their source image. They are treated as pending and will be regenerated on the plate-level rerun."
        )
        lines.extend(f"- {item}" for item in stale_expected_crops)

    if incompatible_expected_crops:
        lines.extend(["", f"INCOMPATIBLE EXPECTED CROPS — WILL REBUILD ({len(incompatible_expected_crops)})"])
        lines.append(
            "These expected PNGs are unreadable or do not match the configured crop dimensions (in either orientation). They are treated as pending."
        )
        lines.extend(f"- {item}" for item in incompatible_expected_crops)

    if partial_images:
        lines.extend(["", f"PARTIALLY COMPLETE PLATES — NON-BLOCKING ({len(partial_images)})"])
        lines.append(
            "Resume is intentionally plate-level: these plates will be realigned/re-exported as a whole, so their existing expected derived crops may be replaced."
        )
        lines.extend(f"- {item}" for item in partial_images)

    if unexpected_crop_pngs:
        lines.extend(["", f"UNEXPECTED CROP PNGS — NON-BLOCKING ({len(unexpected_crop_pngs)})"])
        lines.append("These files are not part of the current metadata-defined crop set; review/remove them if they are stale.")
        lines.extend(f"- {item}" for item in unexpected_crop_pngs)

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
    parser.add_argument(
        "--no-fiji-handoff-path-rules",
        action="store_true",
        help="skip only semicolon path restrictions used by the composed Fiji macro handoff",
    )
    args = parser.parse_args()

    require_fiji_handoff_paths = not args.no_fiji_handoff_path_rules
    config = load_config(args.config, require_fiji_handoff_paths=require_fiji_handoff_paths)
    validate_project_csvs(config)
    lines, problems, pending_rows = build_report(
        config,
        require_fiji_handoff_paths=require_fiji_handoff_paths,
    )
    text = "\n".join(lines) + "\n"
    print(text, end="")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
    write_pending_csv(args.pending_images_csv, pending_rows)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
