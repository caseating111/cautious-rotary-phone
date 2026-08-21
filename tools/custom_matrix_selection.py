from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter

APP_DIR = Path.home() / ".cautious-rotary-phone"
LAST_SELECTION_FILE = APP_DIR / "last_matrix_selection.json"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"CSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_selection(selection: dict) -> dict:
    if not isinstance(selection, dict):
        raise SystemExit("Selection recipe must be a JSON object.")
    groups = selection.get("groups", [])
    conditions = selection.get("conditions", [])
    states = selection.get("states", ["Top", "Low"])
    if not isinstance(groups, list) or not groups:
        raise SystemExit("Selection recipe needs at least one experiment/set group.")
    if not isinstance(conditions, list) or not conditions:
        raise SystemExit("Selection recipe needs at least one condition/type.")
    if not isinstance(states, list) or not states:
        raise SystemExit("Selection recipe needs at least one state (Top or Low).")
    clean_states = []
    for state in states:
        value = str(state).strip().title()
        if value not in {"Top", "Low"}:
            raise SystemExit(f"Unsupported matrix state: {state!r}")
        if value not in clean_states:
            clean_states.append(value)

    clean_groups = []
    identities: set[tuple[str, str]] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise SystemExit("Each selected group must be an object.")
        exp = str(group.get("experiment", "")).strip()
        set_name = str(group.get("set", "")).strip()
        columns_raw = group.get("columns", [])
        if not exp or not set_name or not isinstance(columns_raw, list) or not columns_raw:
            raise SystemExit("Each selected group needs experiment, set and at least one column.")
        columns = []
        for raw in columns_raw:
            try:
                column = int(raw)
            except (TypeError, ValueError) as exc:
                raise SystemExit(f"Invalid selected grid column: {raw!r}") from exc
            if column <= 0:
                raise SystemExit(f"Selected grid columns must be positive: {column}")
            if column not in columns:
                columns.append(column)
        key = (exp.casefold(), set_name.casefold())
        if key in identities:
            raise SystemExit(f"Duplicate experiment/set selection: {exp}/{set_name}")
        identities.add(key)
        clean_groups.append({"experiment": exp, "set": set_name, "columns": columns})

    clean_conditions = []
    seen_conditions: set[str] = set()
    for condition in conditions:
        value = str(condition).strip()
        if not value:
            continue
        key = value.casefold()
        if key not in seen_conditions:
            seen_conditions.add(key)
            clean_conditions.append(value)
    if not clean_conditions:
        raise SystemExit("Selection recipe has no usable condition/type names.")

    return {"groups": clean_groups, "conditions": clean_conditions, "states": clean_states}


def save_last_selection(selection: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SELECTION_FILE.write_text(json.dumps(normalize_selection(selection), indent=2) + "\n", encoding="utf-8")


def filter_project_csvs(config: dict, selection: dict, destination: Path) -> dict[str, Path]:
    selection = normalize_selection(selection)
    grid_fields, grid_rows = read_rows(Path(config["grid_csv"]))
    image_fields, image_rows = read_rows(Path(config["images_csv"]))
    condition_fields, condition_rows = read_rows(Path(config["condition_order_csv"]))

    columns_by_group = {
        (group["experiment"].casefold(), group["set"].casefold()): set(group["columns"])
        for group in selection["groups"]
    }
    condition_keys = {value.casefold() for value in selection["conditions"]}

    filtered_grid = []
    actual_columns: dict[tuple[str, str], set[int]] = {}
    for row in grid_rows:
        key = ((row.get("Experiment") or "").strip().casefold(), (row.get("Set") or "").strip().casefold())
        if key not in columns_by_group:
            continue
        try:
            column = int((row.get("Column") or "").strip())
        except ValueError:
            continue
        if column in columns_by_group[key]:
            filtered_grid.append(row)
            actual_columns.setdefault(key, set()).add(column)

    missing_columns = []
    for group in selection["groups"]:
        key = (group["experiment"].casefold(), group["set"].casefold())
        for column in group["columns"]:
            if column not in actual_columns.get(key, set()):
                missing_columns.append(f"{group['experiment']}/{group['set']} column {column}")
    if missing_columns:
        raise SystemExit("Selected grid columns are not present in grid.csv:\n" + "\n".join(missing_columns))

    filtered_images = [
        row
        for row in image_rows
        if (
            ((row.get("Experiment") or "").strip().casefold(), (row.get("Set") or "").strip().casefold())
            in columns_by_group
            and (row.get("Type") or "").strip().casefold() in condition_keys
        )
    ]
    if not filtered_images:
        raise SystemExit("No images.csv rows match the selected experiment/set groups and conditions.")

    filtered_conditions = [
        row for row in condition_rows if (row.get("Type") or "").strip().casefold() in condition_keys
    ]
    present_conditions = {(row.get("Type") or "").strip().casefold() for row in filtered_conditions}
    missing_conditions = [value for value in selection["conditions"] if value.casefold() not in present_conditions]
    if missing_conditions:
        raise SystemExit("Selected conditions are not present in condition_order.csv: " + ", ".join(missing_conditions))

    destination.mkdir(parents=True, exist_ok=True)
    grid_path = destination / "grid.csv"
    images_path = destination / "images.csv"
    conditions_path = destination / "condition_order.csv"
    write_rows(grid_path, grid_fields, filtered_grid)
    write_rows(images_path, image_fields, filtered_images)
    write_rows(conditions_path, condition_fields, filtered_conditions)
    return {"grid_csv": grid_path, "images_csv": images_path, "condition_order_csv": conditions_path}


def patch_matrix_states(configured_script: Path, states: list[str]) -> None:
    text = configured_script.read_text(encoding="utf-8")
    old = 'STATES_TO_BUILD = ["Top", "Low"]'
    if text.count(old) != 1:
        raise SystemExit("Configured matrix script no longer has the expected STATES_TO_BUILD setting.")
    text = text.replace(old, f"STATES_TO_BUILD = {states!r}", 1)
    configured_script.write_text(text, encoding="utf-8")


def run_selection(selection: dict, no_open_output: bool = False) -> Path:
    selection = normalize_selection(selection)
    config = pillow_adapter.load_config()
    # Validate the authoritative complete project before deriving a sparse temporary view.
    # The standard project validator intentionally requires contiguous 1..GridCols rows,
    # while a focused comparison deliberately keeps only selected original column IDs.
    pillow_adapter.validate_csvs(config)

    APP_DIR.mkdir(parents=True, exist_ok=True)
    output_root = pillow_adapter.ensure_matrix_output_root(config)
    before = pillow_adapter.child_directories(output_root)

    with tempfile.TemporaryDirectory(prefix="custom-matrix-", dir=APP_DIR) as temp:
        temp_root = Path(temp)
        csv_root = temp_root / "csv"
        filtered = filter_project_csvs(config, selection, csv_root)
        custom_config = dict(config)
        custom_config.update({key: str(path) for key, path in filtered.items()})

        selected_crops = pillow_adapter.validate_unique_crop_matches(
            Path(config["crop_output"]),
            filtered["grid_csv"], filtered["images_csv"],
            allow_missing=False,
        )
        staged_root = temp_root / "crops"
        staged_crops = pillow_adapter.stage_selected_crops(selected_crops, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged_crops,
            strict=True,
        )
        configured = pillow_adapter.configured_copy("matrices", custom_config, image_root=staged_root)
        patch_matrix_states(configured, selection["states"])
        result = subprocess.run([sys.executable, str(configured)], check=False)

    after = pillow_adapter.child_directories(output_root)
    if result.returncode != 0:
        pillow_adapter.cleanup_empty_new_directories(before, after)
        raise SystemExit(result.returncode)
    output = pillow_adapter.newest_new_directory(before, after)
    if output is None or not pillow_adapter.directory_has_content(output):
        raise SystemExit("Custom matrix job returned success but produced no non-empty output folder.")
    save_last_selection(selection)
    pillow_adapter.record_output(output)
    if not no_open_output:
        pillow_adapter.open_output(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a focused matrix from existing validated crops.")
    parser.add_argument("selection_json", type=Path)
    parser.add_argument("--no-open-output", action="store_true")
    args = parser.parse_args()
    try:
        selection = json.loads(args.selection_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read selection recipe: {exc}") from exc
    output = run_selection(selection, no_open_output=args.no_open_output)
    print(f"Custom matrix output: {output}")


if __name__ == "__main__":
    main()
