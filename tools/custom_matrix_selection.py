from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".cautious-rotary-phone"
LAST_SELECTION_FILE = APP_DIR / "last_matrix_selection.json"
REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCRIPT = REPO_ROOT / "existing scripts clean" / "make_matrices.py"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise SystemExit(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_selection(selection: dict) -> dict:
    groups = selection.get("groups")
    conditions = selection.get("conditions")
    states = selection.get("states")
    if not isinstance(groups, list) or not groups:
        raise SystemExit("Selection recipe has no experiment/set groups.")
    if not isinstance(conditions, list) or not conditions:
        raise SystemExit("Selection recipe has no conditions.")
    if not isinstance(states, list) or not states:
        raise SystemExit("Selection recipe has no states.")

    clean_states = []
    for state in states:
        value = str(state).strip()
        if value not in {"Top", "Low"}:
            raise SystemExit(f"Unsupported matrix state: {value!r}")
        if value not in clean_states:
            clean_states.append(value)

    clean_groups = []
    identities: set[tuple[str, str]] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise SystemExit("Each selected group must be an object.")
        exp = str(group.get("experiment", "")).strip()
        set_name = str(group.get("set", "")).strip()
        raw_columns = group.get("columns")
        if not exp or not set_name:
            raise SystemExit("Selected groups require experiment and set names.")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise SystemExit(f"Selected group {exp}/{set_name} has no grid columns.")
        columns = []
        for raw in raw_columns:
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
    LAST_SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
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
        wanted = columns_by_group.get(key)
        if wanted is None:
            continue
        try:
            column = int((row.get("Column") or "").strip())
        except ValueError:
            continue
        if column not in wanted:
            continue
        filtered_grid.append(row)
        actual_columns.setdefault(key, set()).add(column)

    for group in selection["groups"]:
        key = (group["experiment"].casefold(), group["set"].casefold())
        missing = sorted(set(group["columns"]) - actual_columns.get(key, set()))
        if missing:
            raise SystemExit(
                f"Selected grid columns are unavailable for {group['experiment']}/{group['set']}: {missing}"
            )

    filtered_images = [
        row
        for row in image_rows
        if ((row.get("Experiment") or "").strip().casefold(), (row.get("Set") or "").strip().casefold()) in columns_by_group
        and (row.get("Type") or "").strip().casefold() in condition_keys
    ]
    filtered_conditions = [
        row for row in condition_rows if (row.get("Type") or "").strip().casefold() in condition_keys
    ]

    if not filtered_grid:
        raise SystemExit("Selection produced no grid rows.")
    if not filtered_images:
        raise SystemExit("Selection produced no image rows.")
    if not filtered_conditions:
        raise SystemExit("Selection produced no condition rows.")

    destination.mkdir(parents=True, exist_ok=True)
    paths = {
        "grid_csv": destination / "grid.csv",
        "images_csv": destination / "images.csv",
        "condition_order_csv": destination / "condition_order.csv",
    }
    write_rows(paths["grid_csv"], grid_fields, filtered_grid)
    write_rows(paths["images_csv"], image_fields, filtered_images)
    write_rows(paths["condition_order_csv"], condition_fields, filtered_conditions)
    return paths


def patch_matrix_states(source: str, states: list[str]) -> str:
    old = 'STATES_TO_BUILD = ["Top", "Low"]'
    new = "STATES_TO_BUILD = " + repr(states)
    if source.count(old) != 1:
        raise SystemExit("Established matrix script state setting changed; refusing to guess where to patch.")
    return source.replace(old, new, 1)


def stage_matrix_script(destination: Path, states: list[str]) -> Path:
    if not MATRIX_SCRIPT.is_file():
        raise SystemExit(f"Established matrix script not found: {MATRIX_SCRIPT}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(patch_matrix_states(MATRIX_SCRIPT.read_text(encoding="utf-8"), states), encoding="utf-8")
    return destination


def expected_output_names(selection: dict) -> set[str]:
    clean = normalize_selection(selection)
    return {
        f"{group['experiment']}_{group['set']}_{state}_MATRIX.png"
        for group in clean["groups"]
        for state in clean["states"]
    }


def verify_expected_outputs(output_folder: Path, selection: dict) -> None:
    expected = expected_output_names(selection)
    actual = {path.name for path in output_folder.glob("*.png") if path.is_file() and path.stat().st_size > 0}
    missing = sorted(expected - actual)
    if missing:
        raise SystemExit("Focused matrix output is incomplete; missing: " + ", ".join(missing))


def run_matrix_script(script: Path, cwd: Path | None = None) -> None:
    result = subprocess.run([sys.executable, str(script)], cwd=cwd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Established matrix renderer failed with exit code {result.returncode}.")


def copy_selected_crops(selected: list[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for source in selected:
        target = destination / source.name
        if target.exists():
            raise SystemExit(f"Duplicate staged crop filename: {target.name}")
        shutil.copy2(source, target)
