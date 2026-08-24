import sys
import types

sys.modules.setdefault("pandas", types.ModuleType("pandas"))

from tools.run_four_point_batch_from_config import (
    SOURCE_MACRO,
    configure_source_settings,
    enhance_four_point_macro,
)


def config():
    return {
        "grid_csv": "grid.csv",
        "image_root": "images",
        "crop_output": "crops",
        "crop_width": 130,
        "crop_height": 546,
        "batch_grid_qc": "1",
        "hide_source_during_alignment": "1",
    }


def test_register_only_setting_does_not_require_crop_destination():
    source = """replacementManifest = "path here";
gridFile   = "path here";
imagesFile = "path here";
stateFile  = "path here";
inputRoot  = "path here";
outputRoot = "path here";
CROP_W = 130;
CROP_H = 546;"""
    result = configure_source_settings(source, config(), register_only=True)
    assert "registerOnly = 1;" in result
    assert 'outputRoot = "";' in result


def test_default_setting_remains_crop_export_mode():
    source = """replacementManifest = "path here";
gridFile   = "path here";
imagesFile = "path here";
stateFile  = "path here";
inputRoot  = "path here";
outputRoot = "path here";
CROP_W = 130;
CROP_H = 546;"""
    result = configure_source_settings(source, config(), register_only=False)
    assert "registerOnly = 0;" in result
    assert 'outputRoot = "crops";' in result


def test_register_only_macro_handoff_precedes_crop_bounds_and_uses_registration_counter():
    source = SOURCE_MACRO.read_text(encoding="utf-8")
    result = enhance_four_point_macro(source, register_only=True)
    branch = result.index("if (registerOnly)")
    assert result.index("getDimensions(sourceW", branch - 120) < branch
    branch_text = result[branch : branch + 1200]
    assert "close();" in branch_text
    assert (
        branch_text.index("close();")
        < branch_text.index("registeredImages++;")
        < branch_text.index("continue;")
    )
    assert 'workflowLog("REGISTERED - "' in branch_text
    assert "gridCoordinateHandoff" in branch_text
    assert "stateFile" not in branch_text
    assert "archiveReplacementCrops" not in branch_text
    assert "saveAs(" not in branch_text
    assert "ACCEPT: Register grid only." in result
    assert "ACCEPT: Export crops." not in result
    assert "Registered images:" in result
    assert "Outputs saved under:" not in result
    assert "requireCropFits(" in result[branch + 1200 :]
