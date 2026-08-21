from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.custom_matrix_preview import PreviewResult, representative_selection
    from tools.presentation_normalize import normalize_staged_crops
    from tools.run_custom_matrix_job import inspect_selected_inputs
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from custom_matrix_preview import PreviewResult, representative_selection
    from presentation_normalize import normalize_staged_crops
    from run_custom_matrix_job import inspect_selected_inputs


def build_preview(selection: dict) -> PreviewResult:
    selection = custom.normalize_selection(selection)
    config = pillow_adapter.load_config()
    inspect_selected_inputs(config, selection)
    preview_selection = representative_selection(selection)
    range_dir = custom.APP_DIR / "display-ranges"

    custom.APP_DIR.mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="matrix-presentation-preview-", dir=custom.APP_DIR)
    root = Path(temp.name)
    try:
        filtered = custom.filter_project_csvs(config, preview_selection, root / "csv")
        preview_config = dict(config)
        preview_config.update({key: str(path) for key, path in filtered.items()})
        preview_output = root / "output"
        preview_config["matrix_output"] = str(preview_output)

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
            image_root=Path(config["image_root"]),
        )
        configured = pillow_adapter.configured_copy("matrices", preview_config, image_root=staged_root)
        custom.patch_matrix_states(configured, preview_selection["states"])
        result = subprocess.run([sys.executable, str(configured)], check=False)
        if result.returncode != 0:
            raise SystemExit("Representative presentation preview failed.")
        images = sorted(preview_output.rglob("*.png"))
        if len(images) != 1:
            raise SystemExit(f"Expected one representative presentation preview image, found {len(images)}.")
        return PreviewResult(temp, images[0])
    except BaseException:
        temp.cleanup()
        raise