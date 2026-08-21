from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import run_existing_pillow_from_config as pillow_adapter
except ModuleNotFoundError:
    import run_existing_pillow_from_config as pillow_adapter


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
