from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.run_custom_matrix_job import validate_selected_freshness
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from run_custom_matrix_job import validate_selected_freshness


class PreviewResult:
    def __init__(self, temp: tempfile.TemporaryDirectory, image: Path) -> None:
        self.temp = temp
        self.image = image

    def cleanup(self) -> None:
        self.temp.cleanup()


def output_count(selection: dict) -> int:
    normalized = custom.normalize_selection(selection)
    return len(normalized["groups"]) * len(normalized["states"])


def representative_selection(selection: dict) -> dict:
    normalized = custom.normalize_selection(selection)
    return {
        "groups": [normalized["groups"][0]],
        "conditions": list(normalized["conditions"]),
        "states": [normalized["states"][0]],
    }


def build_preview(selection: dict) -> PreviewResult:
    selection = custom.normalize_selection(selection)
    config = pillow_adapter.load_config()
    preview_selection = representative_selection(selection)

    custom.APP_DIR.mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="matrix-preview-", dir=custom.APP_DIR)
    root = Path(temp.name)
    try:
        csv_root = root / "csv"
        filtered = custom.filter_project_csvs(config, preview_selection, csv_root)
        preview_config = dict(config)
        preview_config.update({key: str(path) for key, path in filtered.items()})
        preview_output = root / "output"
        preview_config["matrix_output"] = str(preview_output)

        selected_crops = pillow_adapter.validate_unique_crop_matches(
            Path(config["crop_output"]), filtered["grid_csv"], filtered["images_csv"],
            states=preview_selection["states"],
        )
        validate_selected_freshness(config, filtered, selected_crops)
        staged_root = root / "crops"
        staged_crops = pillow_adapter.stage_selected_crops(selected_crops, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged_crops,
            strict=True,
        )
        configured = pillow_adapter.configured_copy("matrices", preview_config, image_root=staged_root)
        custom.patch_matrix_states(configured, preview_selection["states"])
        result = subprocess.run([sys.executable, str(configured)], check=False)
        if result.returncode != 0:
            raise SystemExit("Representative custom-matrix preview failed.")

        images = sorted(preview_output.rglob("*.png"))
        if len(images) != 1:
            raise SystemExit(f"Expected one representative preview image, found {len(images)}.")
        return PreviewResult(temp, images[0])
    except BaseException:
        temp.cleanup()
        raise
