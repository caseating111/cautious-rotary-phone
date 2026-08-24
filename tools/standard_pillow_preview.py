from __future__ import annotations

import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.custom_matrix_preview import PreviewResult, build_preview as build_matrix_preview
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from custom_matrix_preview import PreviewResult, build_preview as build_matrix_preview


def full_matrix_selection(config: dict) -> dict:
    _, grid_rows = custom.read_rows(Path(config["grid_csv"]))
    _, condition_rows = custom.read_rows(Path(config["condition_order_csv"]))
    columns: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in grid_rows:
        key = ((row.get("Experiment") or "").strip(), (row.get("Set") or "").strip())
        column = int((row.get("Column") or "0").strip())
        if column not in columns[key]:
            columns[key].append(column)
    groups = [
        {"experiment": exp, "set": set_name, "columns": sorted(values)}
        for (exp, set_name), values in columns.items()
    ]
    conditions = [
        (row.get("Type") or "").strip()
        for row in sorted(condition_rows, key=lambda row: int((row.get("Order") or "0").strip()))
    ]
    return custom.normalize_selection({"groups": groups, "conditions": conditions, "states": ["Top", "Low"]})


def estimated_output_count(alias: str, config: dict, crop_count: int | None = None) -> int:
    if alias == "matrices":
        selection = full_matrix_selection(config)
        return len(selection["groups"]) * len(selection["states"])
    if alias in {"all-strains", "all-strains-dedup"}:
        return 2
    if alias == "label-individual":
        return int(crop_count or 0)
    raise SystemExit(f"Unsupported Pillow preview job: {alias}")


def patch_first_state(configured_script: Path) -> None:
    text = configured_script.read_text(encoding="utf-8")
    old = 'STATES_TO_BUILD = ["Top", "Low"]'
    if text.count(old) != 1:
        raise SystemExit("Configured all-strains script no longer has the expected STATES_TO_BUILD setting.")
    configured_script.write_text(text.replace(old, 'STATES_TO_BUILD = ["Top"]', 1), encoding="utf-8")


def build_preview(alias: str) -> PreviewResult:
    config = pillow_adapter.load_config()
    pillow_adapter.validate_csvs(config)
    pillow_adapter.validate_source_readiness_if_configured(config)

    if alias == "matrices":
        return build_matrix_preview(full_matrix_selection(config))
    if alias not in {"all-strains", "all-strains-dedup", "label-individual"}:
        raise SystemExit(f"Unsupported Pillow preview job: {alias}")

    crop_root = Path(config["crop_output"])
    selected = pillow_adapter.validate_unique_crop_matches(
        crop_root,
        Path(config["grid_csv"]),
        Path(config["images_csv"]),
    )
    if not selected:
        raise SystemExit("No validated crops are available to preview.")

    pillow_adapter.APP_DIR.mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix=f"{alias}-preview-", dir=pillow_adapter.APP_DIR)
    root = Path(temp.name)
    try:
        staged_root = root / "crops"
        to_stage = selected[:1] if alias == "label-individual" else selected
        staged = pillow_adapter.stage_selected_crops(to_stage, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged,
            strict=True,
        )
        preview_config = dict(config)
        preview_config["matrix_output"] = str(root / "output")
        configured = pillow_adapter.configured_copy(alias, preview_config, image_root=staged_root)
        if alias in {"all-strains", "all-strains-dedup"}:
            patch_first_state(configured)
        result = subprocess.run([sys.executable, str(configured)], check=False)
        if result.returncode != 0:
            raise SystemExit(f"Representative {alias} preview failed.")

        output_root = Path(preview_config["matrix_output"])
        images = sorted(
            path for path in output_root.rglob("*")
            if path.is_file() and path.suffix.lower() in pillow_adapter.IMAGE_EXTENSIONS
        )
        if len(images) != 1:
            raise SystemExit(f"Expected one representative {alias} preview image, found {len(images)}.")
        return PreviewResult(temp, images[0])
    except BaseException:
        temp.cleanup()
        raise
