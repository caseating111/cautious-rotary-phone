from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

try:
    from tools.validate_project_csvs import validate
except ModuleNotFoundError:
    from validate_project_csvs import validate

APP_DIR = Path.home() / ".cautious-rotary-phone"
DEFAULT_CONFIG = APP_DIR / "config.json"
DEFAULT_REVIEW = APP_DIR / "images_reconciliation.csv"
DEFAULT_CANDIDATE = APP_DIR / "images_candidate.csv"
OUTPUT_FIELDS = ["Filename", "Experiment", "Set", "Type"]


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["grid_csv", "condition_order_csv"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise SystemExit("Missing config values: " + ", ".join(missing))
    return data


def read_review(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Reconciliation file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Filename", "Folder", "Experiment", "Set", "Type", "Status"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Reconciliation file missing columns: {', '.join(sorted(missing))}")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def candidate_rows(review: list[dict[str, str]]) -> list[dict[str, str]]:
    source_rows = [row for row in review if row.get("Folder", "")]
    filenames = [row.get("Filename", "") for row in source_rows]
    duplicate_names = sorted(name for name, count in Counter(filenames).items() if name and count > 1)
    if duplicate_names:
        raise SystemExit("Duplicate source basenames cannot be represented in images.csv: " + ", ".join(duplicate_names))

    incomplete = [
        row.get("Filename", "<blank>")
        for row in source_rows
        if not all(row.get(field, "") for field in OUTPUT_FIELDS)
    ]
    if incomplete:
        raise SystemExit("Metadata still incomplete for: " + ", ".join(incomplete))

    return [
        {field: row.get(field, "") for field in OUTPUT_FIELDS}
        for row in source_rows
    ]


def write_candidate(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a validated candidate images.csv from the reconciliation review without overwriting the authoritative file."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()

    config = load_config(args.config)
    rows = candidate_rows(read_review(args.review))
    write_candidate(args.output, rows)

    problems = validate(
        Path(config["grid_csv"]),
        args.output,
        Path(config["condition_order_csv"]),
    )
    if problems:
        args.output.unlink(missing_ok=True)
        print("Candidate rejected by existing project CSV validation:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(f"Validated candidate written: {args.output}")
    print(f"Rows: {len(rows)}")
    print("Authoritative images.csv was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
