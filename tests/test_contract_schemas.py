from __future__ import annotations

import json
from pathlib import Path

from tools.applets.registry import APPLETS, validate_registry

ROOT = Path(__file__).resolve().parents[1]


def read_schema(name: str) -> dict:
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def test_workflow_contract_schemas_are_json_and_versioned() -> None:
    for name, title in (
        ("workflow_project_state.schema.json", "WorkflowProjectState"),
        ("crop_size_calibration.schema.json", "CropSizeCalibration"),
        ("crop_result.schema.json", "CropResult"),
        ("grid_coordinate_asset.schema.json", "GridCoordinateAsset"),
        ("rotation_result.schema.json", "RotationResult"),
        ("visibility_result.schema.json", "VisibilityResult"),
        ("annotation_result.schema.json", "AnnotationResult"),
    ):
        schema = read_schema(name)
        assert schema["title"] == title
        assert schema["properties"]["contract_version"] == {"const": 1}
        assert schema["type"] == "object"


def test_registry_declares_result_contracts_for_each_geometry_consumer() -> None:
    validate_registry()
    by_key = {applet.key: applet for applet in APPLETS}
    assert "workflow_project_state.schema.json" in by_key["project-setup"].contracts
    assert set(by_key["crop"].contracts) == {
        "crop_size_calibration.schema.json",
        "crop_result.schema.json",
    }
    assert "grid_coordinate_asset.schema.json" in by_key["visibility"].contracts
    assert "grid_coordinate_asset.schema.json" in by_key["annotation"].contracts
    assert "visibility_result.schema.json" in by_key["visibility"].contracts
    assert "annotation_result.schema.json" in by_key["annotation"].contracts
