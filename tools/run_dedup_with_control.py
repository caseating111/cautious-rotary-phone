from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.custom_matrix_preview import PreviewResult
    from tools.output_processing_records import write_output_records
    from tools.standard_pillow_preview import patch_first_state
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter
    from custom_matrix_preview import PreviewResult
    from output_processing_records import write_output_records
    from standard_pillow_preview import patch_first_state


PREFERENCE_FILE = pillow_adapter.APP_DIR / "preferred_wt_source.json"


def canonical_control(name: str) -> str | None:
    compare = " ".join(name.strip().upper().replace("-", " ").split())
    if compare in {"WT X", "WT Y"}:
        return compare
    return None


def control_groups(grid_csv: Path) -> dict[tuple[str, str], set[str]]:
    rows = pillow_adapter.read_csv_rows(grid_csv)
    groups: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        control = canonical_control(row.get("Strain", ""))
        if control is None:
            continue
        key = (row.get("Experiment", ""), row.get("Set", ""))
        groups.setdefault(key, set()).add(control)
    return groups


def full_project_selection(config: dict) -> dict:
    columns: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in pillow_adapter.read_csv_rows(Path(config["grid_csv"])):
        key = (row.get("Experiment", ""), row.get("Set", ""))
        column = int(row.get("Column", "0"))
        if column not in columns[key]:
            columns[key].append(column)
    condition_rows = pillow_adapter.read_csv_rows(Path(config["condition_order_csv"]))
    conditions = [
        row.get("Type", "")
        for row in sorted(condition_rows, key=lambda row: int(row.get("Order", "0")))
        if row.get("Type", "")
    ]
    return {
        "groups": [
            {"experiment": exp, "set": set_name, "columns": sorted(values)}
            for (exp, set_name), values in columns.items()
        ],
        "conditions": conditions,
        "states": ["Top", "Low"],
    }


def load_preferred_source(path: Path = PREFERENCE_FILE) -> tuple[str, str] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    experiment = str(data.get("experiment", "")).strip()
    set_name = str(data.get("set", "")).strip()
    if not experiment or not set_name:
        return None
    return experiment, set_name


def save_preferred_source(experiment: str, set_name: str, path: Path = PREFERENCE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"experiment": experiment.strip(), "set": set_name.strip()}, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_control_source(config: dict, experiment: str, set_name: str) -> set[str]:
    experiment = experiment.strip()
    set_name = set_name.strip()
    if not experiment or not set_name:
        raise SystemExit("Preferred control source needs both Experiment and Set.")
    groups = control_groups(Path(config["grid_csv"]))
    controls = groups.get((experiment, set_name), set())
    if not controls:
        available = ", ".join(f"{exp}/{set_value}" for exp, set_value in sorted(groups)) or "none"
        raise SystemExit(
            f"{experiment}/{set_name} has no WT X/WT Y control rows in grid.csv. "
            f"Groups with recognised controls: {available}"
        )
    return controls


def patch_preferred_control(configured_script: Path, experiment: str, set_name: str) -> None:
    text = configured_script.read_text(encoding="utf-8")
    old = '''            if (
                row["experiment"] == "E2"
                and row["set"] == "A"
            ):'''
    new = f'''            if (
                row["experiment"] == {experiment!r}
                and row["set"] == {set_name!r}
            ):'''
    if text.count(old) != 1:
        raise SystemExit("Deduplicated all-strains script no longer has the expected E2/A preference block.")
    configured_script.write_text(text.replace(old, new, 1), encoding="utf-8")


def build_preview(experiment: str, set_name: str) -> PreviewResult:
    config = pillow_adapter.load_config()
    pillow_adapter.validate_csvs(config)
    pillow_adapter.validate_source_readiness_if_configured(config)
    validate_control_source(config, experiment, set_name)

    selected_crops = pillow_adapter.validate_unique_crop_matches(
        Path(config["crop_output"]),
        Path(config["grid_csv"]),
        Path(config["images_csv"]),
        allow_missing=False,
    )
    if not selected_crops:
        raise SystemExit("No validated crops are available to preview.")

    pillow_adapter.APP_DIR.mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="dedup-control-preview-", dir=pillow_adapter.APP_DIR)
    root = Path(temp.name)
    try:
        staged_root = root / "crops"
        staged = pillow_adapter.stage_selected_crops(selected_crops, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged,
            strict=True,
        )
        preview_config = dict(config)
        preview_config["matrix_output"] = str(root / "output")
        configured = pillow_adapter.configured_copy("all-strains-dedup", preview_config, image_root=staged_root)
        patch_preferred_control(configured, experiment.strip(), set_name.strip())
        patch_first_state(configured)
        result = subprocess.run([sys.executable, str(configured)], check=False)
        if result.returncode != 0:
            raise SystemExit("Representative deduplicated all-strains preview failed.")

        images = sorted(
            path for path in Path(preview_config["matrix_output"]).rglob("*")
            if path.is_file() and path.suffix.lower() in pillow_adapter.IMAGE_EXTENSIONS
        )
        if len(images) != 1:
            raise SystemExit(f"Expected one representative deduplicated preview image, found {len(images)}.")
        return PreviewResult(temp, images[0])
    except BaseException:
        temp.cleanup()
        raise


def run(experiment: str, set_name: str, no_open_output: bool = False) -> Path:
    config = pillow_adapter.load_config()
    pillow_adapter.validate_csvs(config)
    pillow_adapter.validate_source_readiness_if_configured(config)
    controls = validate_control_source(config, experiment, set_name)

    crop_root = Path(config["crop_output"])
    selected_crops = pillow_adapter.validate_unique_crop_matches(
        crop_root,
        Path(config["grid_csv"]),
        Path(config["images_csv"]),
        allow_missing=False,
    )
    output_root = pillow_adapter.ensure_matrix_output_root(config)
    before = pillow_adapter.child_directories(output_root)
    pillow_adapter.APP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dedup-control-", dir=pillow_adapter.APP_DIR) as temp:
        staged_root = Path(temp)
        staged_crops = pillow_adapter.stage_selected_crops(selected_crops, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged_crops,
            strict=True,
        )
        configured = pillow_adapter.configured_copy("all-strains-dedup", config, image_root=staged_root)
        patch_preferred_control(configured, experiment.strip(), set_name.strip())
        result = subprocess.run([sys.executable, str(configured)], check=False)

    after = pillow_adapter.child_directories(output_root)
    if result.returncode != 0:
        pillow_adapter.cleanup_empty_new_directories(before, after)
        raise SystemExit(result.returncode)
    output = pillow_adapter.newest_new_directory(before, after)
    if output is None or not pillow_adapter.directory_has_content(output):
        raise SystemExit("Deduplicated all-strains job returned success but produced no non-empty output folder.")
    pillow_adapter.record_output(output)
    save_preferred_source(experiment, set_name)
    required_crops = len(
        pillow_adapter.expected_crop_contract(Path(config["grid_csv"]), Path(config["images_csv"]))
    )
    write_output_records(
        output_root,
        output,
        output_type="all strains (deduplicated controls)",
        selection=full_project_selection(config),
        required_crops=required_crops,
        available_crops=len(selected_crops),
        used_crops=len(selected_crops),
        display_mode="raw",
        control_source={"experiment": experiment.strip(), "set": set_name.strip()},
    )
    print(
        f"Preferred control source: {experiment.strip()}/{set_name.strip()} "
        f"({', '.join(sorted(controls))}; missing recognised controls fall back to the script's first available candidate)."
    )
    if not no_open_output:
        pillow_adapter.open_output(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deduplicated all-strains output with a chosen preferred WT source.")
    parser.add_argument("experiment")
    parser.add_argument("set")
    parser.add_argument("--no-open-output", action="store_true")
    args = parser.parse_args()
    output = run(args.experiment, args.set, no_open_output=args.no_open_output)
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
