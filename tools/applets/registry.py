from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


@dataclass(frozen=True)
class Applet:
    key: str
    label: str
    module: str
    contracts: tuple[str, ...]
    prerequisite: str


APPLETS = (
    Applet(
        "v10",
        "V10 workbook adapter",
        "tools.applets.v10_adapter",
        ("project_model.schema.json", "plate_layout.schema.json"),
        "V10 workbook",
    ),
    Applet(
        "project-setup",
        "Project setup and working-copy rename",
        "tools.applets.project_setup",
        ("project_model.schema.json", "workflow_project_state.schema.json"),
        "project model",
    ),
    Applet(
        "layout",
        "Plate layout derivation",
        "tools.applets.plate_layout",
        ("plate_layout.schema.json",),
        "project model or explicit layout",
    ),
    Applet(
        "orientation",
        "Whole-plate orientation",
        "tools.applets.plate_orientation",
        ("rotation_result.schema.json",),
        "source image",
    ),
    Applet(
        "crop",
        "Plate crop preprocessing",
        "tools.applets.plate_crop",
        ("crop_size_calibration.schema.json", "crop_result.schema.json"),
        "source image",
    ),
    Applet(
        "visibility",
        "Visibility adjustment",
        "tools.applets.visibility",
        (
            "plate_layout.schema.json",
            "grid_coordinate_asset.schema.json",
            "visibility_result.schema.json",
        ),
        "accepted grid coordinates",
    ),
    Applet(
        "annotation",
        "Annotation and composition",
        "tools.applets.annotation",
        (
            "annotation_request.schema.json",
            "annotation_result.schema.json",
            "plate_layout.schema.json",
            "grid_coordinate_asset.schema.json",
        ),
        "accepted grid coordinates",
    ),
)


def validate_registry() -> None:
    keys = set()
    for applet in APPLETS:
        if applet.key in keys:
            raise ValueError(f"Duplicate applet key: {applet.key}")
        keys.add(applet.key)
        for filename in applet.contracts:
            path = CONTRACTS_DIR / filename
            if not path.is_file():
                raise FileNotFoundError(f"Missing applet contract: {path}")
