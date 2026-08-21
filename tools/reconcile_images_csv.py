from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tools.preflight_batch import discover_sources
except ModuleNotFoundError:
    from preflight_batch import discover_sources

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
DEFAULT_REVIEW = APP_DIR / "images_reconciliation.csv"
FIELDS = ["Filename", "Folder", "Experiment", "Set", "Type", "Status"]


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["image_root", "images_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def read_images_csv(path: Path) -> list[dict[str, str]]:
    rows = read_csv_rows(path)
    if not rows and not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Filename", "Experiment", "Set", "Type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path.name}: missing columns: {', '.join(sorted(missing))}")
    return rows


def complete_metadata(row: dict[str, str]) -> bool:
    return all(row.get(field, "").strip() for field in ("Experiment", "Set", "Type"))


def build_rows(
    config: dict,
    previous_review: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    image_root = Path(config["image_root"])
    existing = read_images_csv(Path(config["images_csv"]))
    sources = discover_sources(image_root)

    existing_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in existing:
        existing_by_name[row.get("Filename", "")].append(row)

    draft_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in previous_review or []:
        key = (row.get("Folder", ""), row.get("Filename", ""))
        if all(key):
            draft_by_key[key] = row

    source_counts = Counter(path.name for path in sources)
    source_names = set(source_counts)
    rows: list[dict[str, str]] = []

    for source in sources:
        matches = existing_by_name.get(source.name, [])
        draft = draft_by_key.get((source.parent.name, source.name), {})

        if source_counts[source.name] > 1:
            status = "DUPLICATE_SOURCE_BASENAME"
            metadata = matches[0] if len(matches) == 1 else draft
        elif len(matches) == 1:
            status = "EXISTING"
            metadata = matches[0]
        elif len(matches) > 1:
            status = "DUPLICATE_IMAGES_CSV_ROW"
            metadata = matches[0]
        else:
            metadata = draft
            status = "DRAFT_METADATA_READY" if complete_metadata(draft) else "NEW_SOURCE_NEEDS_METADATA"

        rows.append(
            {
                "Filename": source.name,
                "Folder": source.parent.name,
                "Experiment": metadata.get("Experiment", ""),
                "Set": metadata.get("Set", ""),
                "Type": metadata.get("Type", ""),
                "Status": status,
            }
        )

    for row in existing:
        filename = row.get("Filename", "")
        if filename and filename not in source_names:
            rows.append(
                {
                    "Filename": filename,
                    "Folder": "",
                    "Experiment": row.get("Experiment", ""),
                    "Set": row.get("Set", ""),
                    "Type": row.get("Type", ""),
                    "Status": "CSV_ROW_SOURCE_NOT_FOUND",
                }
            )

    rows.sort(key=lambda row: (row["Folder"], row["Filename"], row["Status"]))
    counts = Counter(row["Status"] for row in rows)
    return rows, dict(counts)


def write_review(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a non-destructive review CSV reconciling source images with images.csv."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()

    previous = read_csv_rows(args.output)
    rows, counts = build_rows(load_config(args.config), previous)
    write_review(args.output, rows)

    print(f"Metadata reconciliation written: {args.output}")
    print(f"Rows: {len(rows)}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    print("Existing images.csv remains authoritative and was not changed.")
    print("Manual draft metadata in this reconciliation file is preserved across rescans.")

    blocking = {
        "NEW_SOURCE_NEEDS_METADATA",
        "DUPLICATE_SOURCE_BASENAME",
        "DUPLICATE_IMAGES_CSV_ROW",
        "CSV_ROW_SOURCE_NOT_FOUND",
    }
    return 1 if any(status in blocking for status in counts) else 0


if __name__ == "__main__":
    raise SystemExit(main())
