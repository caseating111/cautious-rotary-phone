from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

HEADERS = {
    "grid": ["Experiment", "Set", "GridCols", "Column", "Strain"],
    "images": ["Filename", "Experiment", "Set", "Type"],
    "conditions": ["Order", "Type"],
}


def rows(path: Path, required: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = [h.strip() for h in (reader.fieldnames or [])]
        missing = [h for h in required if h not in actual]
        if missing:
            raise ValueError(f"{path.name}: missing columns: {', '.join(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def validate(grid_path: Path, images_path: Path, conditions_path: Path) -> list[str]:
    problems: list[str] = []
    try:
        grid = rows(grid_path, HEADERS["grid"])
        images = rows(images_path, HEADERS["images"])
        conditions = rows(conditions_path, HEADERS["conditions"])
    except ValueError as exc:
        return [str(exc)]

    groups: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
    for line_no, row in enumerate(grid, 2):
        key = (row["Experiment"], row["Set"])
        if not all(key):
            problems.append(f"grid.csv row {line_no}: empty Experiment/Set")
            continue
        try:
            declared = int(row["GridCols"])
            column = int(row["Column"])
        except ValueError:
            problems.append(f"grid.csv row {line_no}: GridCols/Column must be integers")
            continue
        if declared < 1 or column < 1:
            problems.append(f"grid.csv row {line_no}: GridCols/Column must be positive")
            continue
        if not row["Strain"]:
            problems.append(f"grid.csv row {line_no}: empty Strain")
        groups[key].append((declared, column, row["Strain"]))

    for (exp, set_name), entries in sorted(groups.items()):
        declared_values = {entry[0] for entry in entries}
        if len(declared_values) != 1:
            problems.append(f"grid.csv {exp}/{set_name}: inconsistent GridCols {sorted(declared_values)}")
            continue
        declared = next(iter(declared_values))
        columns = [entry[1] for entry in entries]
        duplicates = sorted({c for c in columns if columns.count(c) > 1})
        if duplicates:
            problems.append(f"grid.csv {exp}/{set_name}: duplicate columns {duplicates}")
        actual = sorted(set(columns))
        expected = list(range(1, declared + 1))
        if actual != expected:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"outside range {extra}")
            problems.append(f"grid.csv {exp}/{set_name}: expected columns 1..{declared}; " + ", ".join(detail))

    condition_orders: dict[int, str] = {}
    condition_names: set[str] = set()
    for line_no, row in enumerate(conditions, 2):
        name = row["Type"]
        if not name:
            problems.append(f"condition_order.csv row {line_no}: empty Type")
            continue
        try:
            order = int(row["Order"])
        except ValueError:
            problems.append(f"condition_order.csv row {line_no}: Order must be an integer")
            continue
        if order in condition_orders:
            problems.append(
                f"condition_order.csv: duplicate Order {order} for {condition_orders[order]!r} and {name!r}"
            )
        if name in condition_names:
            problems.append(f"condition_order.csv: duplicate Type {name!r}")
        condition_orders[order] = name
        condition_names.add(name)

    image_filenames: set[str] = set()
    for line_no, row in enumerate(images, 2):
        filename = row["Filename"]
        key = (row["Experiment"], row["Set"])
        type_name = row["Type"]
        if not filename:
            problems.append(f"images.csv row {line_no}: empty Filename")
        elif filename in image_filenames:
            problems.append(f"images.csv: duplicate Filename {filename!r}")
        image_filenames.add(filename)
        if key not in groups:
            problems.append(f"images.csv row {line_no}: {key[0]}/{key[1]} has no grid.csv definition")
        if not type_name:
            problems.append(f"images.csv row {line_no}: empty Type")
        elif type_name not in condition_names:
            problems.append(f"images.csv row {line_no}: Type {type_name!r} absent from condition_order.csv")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate plate-workflow CSV contracts.")
    parser.add_argument("grid_csv", type=Path)
    parser.add_argument("images_csv", type=Path)
    parser.add_argument("condition_order_csv", type=Path)
    args = parser.parse_args()

    problems = validate(args.grid_csv, args.images_csv, args.condition_order_csv)
    if problems:
        print("CSV validation FAILED")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("CSV validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
