from __future__ import annotations

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.output_processing_records import write_output_records
    from tools.preflight_batch import discover_sources, expected_crop_issue, expected_output_names
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from output_processing_records import write_output_records
    from preflight_batch import discover_sources, expected_crop_issue, expected_output_names


def validate_selected_freshness(
    config: dict,
    filtered: dict[str, Path],
    selected_paths: list[Path],
) -> None:
    image_root_value = str(config.get("image_root", "")).strip()
    if not image_root_value:
        return
    image_root = Path(image_root_value)
    sources = discover_sources(image_root)
    source_by_name: dict[str, list[Path]] = defaultdict(list)
    for source in sources:
        source_by_name[source.name.casefold()].append(source)

    _, grid_rows = custom.read_rows(filtered["grid_csv"])
    _, image_rows = custom.read_rows(filtered["images_csv"])
    grid_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in grid_rows:
        grid_by_key[((row.get("Experiment") or "").strip(), (row.get("Set") or "").strip())].append(
            {key: (value or "").strip() for key, value in row.items()}
        )

    crop_by_name = {path.name.casefold(): path for path in selected_paths}
    issues: list[str] = []
    for raw_row in image_rows:
        row = {key: (value or "").strip() for key, value in raw_row.items()}
        filename = row.get("Filename", "")
        matches = source_by_name.get(filename.casefold(), [])
        if len(matches) != 1:
            issues.append(f"{filename}: expected one current source image, found {len(matches)}")
            continue
        source = matches[0]
        grid = grid_by_key.get((row.get("Experiment", ""), row.get("Set", "")), [])
        for expected_name in expected_output_names(row, grid):
            crop = crop_by_name.get(expected_name.casefold())
            if crop is None:
                continue
            issue = expected_crop_issue(
                crop,
                source.stat().st_mtime_ns,
                int(config.get("crop_width", 130)),
                int(config.get("crop_height", 546)),
            )
            if issue:
                issues.append(f"{crop.name}: {issue} ({source.relative_to(image_root)})")
    if issues:
        raise SystemExit(
            "Selected custom-matrix crops are not current relative to their source images:\n"
            + "\n".join(f"  - {item}" for item in issues[:30])
        )


def inspect_selected_inputs(config: dict, selection: dict) -> tuple[int, int]:
    custom.APP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="custom-matrix-check-", dir=custom.APP_DIR) as temp:
        filtered = custom.filter_project_csvs(config, selection, Path(temp))
        contract = pillow_adapter.expected_crop_contract(filtered["grid_csv"], filtered["images_csv"])
        selected_paths = pillow_adapter.validate_unique_crop_matches(
            Path(config["crop_output"]),
            filtered["grid_csv"],
            filtered["images_csv"],
        )
        validate_selected_freshness(config, filtered, selected_paths)
        return len(contract), len(selected_paths)


def run_job(selection: dict, no_open_output: bool = False) -> Path:
    selection = custom.normalize_selection(selection)
    config = pillow_adapter.load_config()
    full_required, full_available = inspect_selected_inputs(config, selection)
    output = custom.run_selection(selection, no_open_output=no_open_output)

    # The exact-crop contract contains both Top and Low. Human records count only states actually rendered.
    rendered_required = full_required * len(selection["states"]) // 2
    rendered_available = full_available * len(selection["states"]) // 2
    write_output_records(
        Path(config["matrix_output"]),
        output,
        output_type="custom matrix",
        selection=selection,
        required_crops=rendered_required,
        available_crops=rendered_available,
        used_crops=rendered_available,
        display_mode="raw",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a focused matrix and record its processing recipe.")
    parser.add_argument("selection_json", type=Path)
    parser.add_argument("--no-open-output", action="store_true")
    args = parser.parse_args()
    try:
        selection = json.loads(args.selection_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read selection recipe: {exc}") from exc
    output = run_job(selection, no_open_output=args.no_open_output)
    print(f"Custom matrix output: {output}")


if __name__ == "__main__":
    main()
