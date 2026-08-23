from __future__ import annotations

import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.preflight_batch import discover_sources, expected_crop_issue, safe_name
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from preflight_batch import discover_sources, expected_crop_issue, safe_name


@dataclass(frozen=True)
class CropInventoryItem:
    experiment: str
    set_name: str
    condition: str
    column: int
    strain: str
    state: str
    source_filename: str
    expected_filename: str
    status: str
    detail: str = ""
    path: str = ""


def selected_inventory(config: dict, selection: dict) -> list[CropInventoryItem]:
    selection = custom.normalize_selection(selection)
    pillow_adapter.validate_csvs(config)
    custom.APP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="crop-inventory-", dir=custom.APP_DIR) as temp:
        filtered = custom.filter_project_csvs(config, selection, Path(temp))
        _, grid_rows = custom.read_rows(filtered["grid_csv"])
        _, image_rows = custom.read_rows(filtered["images_csv"])

    grid_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in grid_rows:
        clean = {key: (value or "").strip() for key, value in row.items()}
        grid_by_key[(clean.get("Experiment", ""), clean.get("Set", ""))].append(clean)

    crop_root = Path(config["crop_output"])
    crop_files: dict[str, list[Path]] = defaultdict(list)
    if crop_root.is_dir():
        for path in crop_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in pillow_adapter.IMAGE_EXTENSIONS:
                crop_files[path.name.casefold()].append(path)

    source_by_name: dict[str, list[Path]] = defaultdict(list)
    image_root_value = str(config.get("image_root", "")).strip()
    image_root = Path(image_root_value) if image_root_value else None
    if image_root is not None:
        for source in discover_sources(image_root):
            source_by_name[source.name.casefold()].append(source)

    wanted_states = set(selection["states"])
    crop_width = int(config.get("crop_width", 130))
    crop_height = int(config.get("crop_height", 546))
    items: list[CropInventoryItem] = []

    for raw_image in image_rows:
        image = {key: (value or "").strip() for key, value in raw_image.items()}
        exp = image.get("Experiment", "")
        set_name = image.get("Set", "")
        condition = image.get("Type", "")
        source_name = image.get("Filename", "")
        source_matches = source_by_name.get(source_name.casefold(), []) if image_root is not None else []

        for grid in sorted(grid_by_key.get((exp, set_name), []), key=lambda row: int(row["Column"])):
            column = int(grid["Column"])
            strain = grid.get("Strain", "")
            for state in ("Top", "Low"):
                if state not in wanted_states:
                    continue
                expected = f"{exp}_{set_name}_{condition}_{column:02d}_{state}_{safe_name(strain)}.png"
                matches = crop_files.get(expected.casefold(), [])
                status = "current"
                detail = ""
                path_text = ""

                if not matches:
                    if image_root is not None and len(source_matches) != 1:
                        status = "source ambiguous" if source_matches else "source missing"
                        detail = (
                            f"crop missing; expected one source image named {source_name}; "
                            f"found {len(source_matches)}"
                        )
                    else:
                        status = "missing"
                elif len(matches) > 1:
                    status = "duplicate"
                    detail = "; ".join(str(path.relative_to(crop_root)) for path in matches[:5])
                else:
                    crop = matches[0]
                    path_text = str(crop.relative_to(crop_root))
                    if image_root is not None:
                        if len(source_matches) != 1:
                            status = "source ambiguous" if source_matches else "source missing"
                            detail = f"expected one source image named {source_name}; found {len(source_matches)}"
                        else:
                            issue = expected_crop_issue(
                                crop,
                                source_matches[0].stat().st_mtime_ns,
                                crop_width,
                                crop_height,
                            )
                            if issue:
                                status = "stale" if issue == "older than source" else "incompatible"
                                detail = issue

                items.append(
                    CropInventoryItem(
                        experiment=exp,
                        set_name=set_name,
                        condition=condition,
                        column=column,
                        strain=strain,
                        state=state,
                        source_filename=source_name,
                        expected_filename=expected,
                        status=status,
                        detail=detail,
                        path=path_text,
                    )
                )

    return items




def source_plates_to_rerun(items: list[CropInventoryItem]) -> list[str]:
    fixable = {"missing", "stale", "incompatible"}
    return sorted(
        {item.source_filename for item in items if item.status in fixable and item.source_filename},
        key=str.casefold,
    )


def inventory_summary(items: list[CropInventoryItem]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[item.status] += 1
    current = counts.pop("current", 0)
    lines = [f"Selected crop cells: {len(items)}", f"Current: {current}"]
    for status in sorted(counts):
        lines.append(f"{status.title()}: {counts[status]}")

    rerun_sources = source_plates_to_rerun(items)
    if rerun_sources:
        lines.extend(["", f"Source plates to rerun ({len(rerun_sources)}):"])
        lines.extend(f"- {name}" for name in rerun_sources)

    problems = [item for item in items if item.status != "current"]
    if problems:
        lines.extend(["", "Items needing attention:"])
        for item in problems[:30]:
            label = (
                f"{item.experiment}/{item.set_name} | {item.condition} | "
                f"col {item.column} {item.strain} | {item.state}: {item.status}"
            )
            if item.detail:
                label += f" — {item.detail}"
            lines.append(label)
        if len(problems) > 30:
            lines.append(f"... plus {len(problems) - 30} more")
    return "\n".join(lines)
