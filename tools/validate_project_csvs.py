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
OUTPUT_NAME_UNSAFE = set('/\\:*?"<>|')


def rows(path: Path, required: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        stripped_headers = [h.strip() for h in raw_headers]
        duplicates = sorted({h for h in stripped_headers if h and stripped_headers.count(h) > 1})
        if duplicates:
            raise ValueError(
                f"{path.name}: duplicate columns after trimming header whitespace: {', '.join(duplicates)}"
            )
        if raw_headers != stripped_headers:
            changed = [raw for raw, clean in zip(raw_headers, stripped_headers) if raw != clean]
            raise ValueError(
                f"{path.name}: column names must not contain surrounding whitespace; fix: "
                + ", ".join(repr(value) for value in changed)
            )
        missing = [h for h in required if h not in raw_headers]
        if missing:
            raise ValueError(f"{path.name}: missing columns: {', '.join(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def raw_field_whitespace_rows(path: Path, field: str) -> list[int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            line_no
            for line_no, row in enumerate(reader, 2)
            if (raw := (row.get(field) or "")) != raw.strip()
        ]


def imagej_line_unsafe(
    problems: list[str],
    file_name: str,
    line_no: int,
    row: dict[str, str],
    fields: list[str],
) -> None:
    for field in fields:
        value = row.get(field, "")
        if "," in value:
            problems.append(
                f"{file_name} row {line_no}: {field} contains a comma, which the reused ImageJ CSV parser cannot safely read"
            )
        if "\n" in value or "\r" in value:
            problems.append(
                f"{file_name} row {line_no}: {field} contains a line break, which the reused ImageJ line parser cannot safely read"
            )


def macro_argument_unsafe(
    problems: list[str],
    file_name: str,
    line_no: int,
    row: dict[str, str],
    fields: list[str],
) -> None:
    for field in fields:
        if ";" in row.get(field, ""):
            problems.append(
                f"{file_name} row {line_no}: {field} contains a semicolon, which conflicts with the composed Fiji macro-argument delimiter"
            )


def output_filename_unsafe(
    problems: list[str],
    file_name: str,
    line_no: int,
    row: dict[str, str],
    fields: list[str],
) -> None:
    for field in fields:
        value = row.get(field, "")
        bad = sorted(set(value) & OUTPUT_NAME_UNSAFE)
        if bad:
            problems.append(
                f"{file_name} row {line_no}: {field} contains filename-unsafe character(s) {''.join(bad)!r}; this value is used directly in crop filenames"
            )


def validate(grid_path: Path, images_path: Path, conditions_path: Path) -> list[str]:
    problems: list[str] = []
    try:
        grid = rows(grid_path, HEADERS["grid"])
        images = rows(images_path, HEADERS["images"])
        conditions = rows(conditions_path, HEADERS["conditions"])
    except ValueError as exc:
        return [str(exc)]

    for line_no in raw_field_whitespace_rows(images_path, "Filename"):
        problems.append(
            f"images.csv row {line_no}: Filename contains surrounding whitespace; "
            "the reused Fiji batch macro matches the raw filename field before trimming and would skip this source"
        )

    groups: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
    for line_no, row in enumerate(grid, 2):
        imagej_line_unsafe(problems, "grid.csv", line_no, row, ["Experiment", "Set", "Strain"])
        macro_argument_unsafe(problems, "grid.csv", line_no, row, ["Experiment", "Set"])
        output_filename_unsafe(problems, "grid.csv", line_no, row, ["Experiment", "Set"])
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
        output_filename_unsafe(problems, "condition_order.csv", line_no, row, ["Type"])
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
        imagej_line_unsafe(problems, "images.csv", line_no, row, ["Experiment", "Set", "Type"])
        macro_argument_unsafe(problems, "images.csv", line_no, row, ["Experiment", "Set", "Type"])
        output_filename_unsafe(problems, "images.csv", line_no, row, ["Experiment", "Set", "Type"])
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
