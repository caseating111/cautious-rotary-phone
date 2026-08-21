from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.output_processing_records import write_output_records
    from tools.presentation_normalize import normalize_staged_crops
    from tools.run_custom_matrix_job import inspect_selected_inputs
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from output_processing_records import write_output_records
    from presentation_normalize import normalize_staged_crops
    from run_custom_matrix_job import inspect_selected_inputs


def run_job(selection: dict, no_open_output: bool = False) -> Path:
    selection = custom.normalize_selection(selection)
    config = pillow_adapter.load_config()
    pillow_adapter.validate_csvs(config)
    inspect_selected_inputs(config, selection)

    custom.APP_DIR.mkdir(parents=True, exist_ok=True)
    range_dir = custom.APP_DIR / "display-ranges"
    output_root = pillow_adapter.ensure_matrix_output_root(config)
    before = pillow_adapter.child_directories(output_root)
    image_root_value = str(config.get("image_root", "")).strip()
    image_root = Path(image_root_value) if image_root_value else None

    with tempfile.TemporaryDirectory(prefix="custom-matrix-presentation-", dir=custom.APP_DIR) as temp:
        root = Path(temp)
        filtered = custom.filter_project_csvs(config, selection, root / "csv")
        custom_config = dict(config)
        custom_config.update({key: str(path) for key, path in filtered.items()})
        contract = pillow_adapter.expected_crop_contract(filtered["grid_csv"], filtered["images_csv"])
        selected_crops = pillow_adapter.validate_unique_crop_matches(
            Path(config["crop_output"]), filtered["grid_csv"], filtered["images_csv"], allow_missing=False
        )
        staged_root = root / "crops"
        staged_crops = pillow_adapter.stage_selected_crops(selected_crops, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged_crops,
            strict=True,
        )
        normalize_staged_crops(
            staged_crops,
            filtered["grid_csv"],
            filtered["images_csv"],
            range_dir,
            image_root=image_root,
        )
        configured = pillow_adapter.configured_copy("matrices", custom_config, image_root=staged_root)
        custom.patch_matrix_states(configured, selection["states"])
        result = subprocess.run([sys.executable, str(configured)], check=False)

    after = pillow_adapter.child_directories(output_root)
    if result.returncode != 0:
        pillow_adapter.cleanup_empty_new_directories(before, after)
        raise SystemExit(result.returncode)
    output = pillow_adapter.newest_new_directory(before, after)
    if output is None or not pillow_adapter.directory_has_content(output):
        raise SystemExit("Presentation custom-matrix job returned success but produced no non-empty output folder.")

    custom.save_last_selection(selection)
    pillow_adapter.record_output(output)
    rendered_count = len(contract) * len(selection["states"]) // 2
    write_output_records(
        output_root,
        output,
        output_type="custom matrix",
        selection=selection,
        required_crops=rendered_count,
        available_crops=rendered_count,
        used_crops=rendered_count,
        display_mode="presentation normalized (archived Fiji plate range)",
    )
    if not no_open_output:
        pillow_adapter.open_output(output)
    return output
