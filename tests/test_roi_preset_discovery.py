from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.roi_preset_gui import (
    HELPER_MARKER,
    PATCH_CALL,
    PREFS_CALL,
    TOOL_MARKER,
    TOOLSET_NAME,
    configured_fiji_root,
    find_roi_click_tools,
    patch_roi_click_tools,
    validated_preset,
)


class RoiPresetDiscoveryTests(unittest.TestCase):
    def test_configured_fiji_root_uses_executable_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fiji = root / "Fiji.app"
            fiji.mkdir()
            executable = fiji / "ImageJ-win64.exe"
            executable.write_text("placeholder", encoding="utf-8")
            config = root / "config.json"
            config.write_text(json.dumps({"fiji_executable": str(executable)}), encoding="utf-8")
            self.assertEqual(configured_fiji_root(config), fiji)

    def test_configured_fiji_root_ignores_non_object_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text("[]\n", encoding="utf-8")
            self.assertIsNone(configured_fiji_root(config))

    def test_find_roi_tool_prefers_normal_toolsets_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            toolsets = root / "macros" / "toolsets"
            toolsets.mkdir(parents=True)
            expected = toolsets / TOOLSET_NAME
            expected.write_text("macro source", encoding="utf-8")
            self.assertEqual(find_roi_click_tools(root), [expected.resolve()])

    def test_find_roi_tool_recurses_when_install_location_is_nonstandard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "plugins" / "custom" / "nested"
            nested.mkdir(parents=True)
            expected = nested / TOOLSET_NAME
            expected.write_text("macro source", encoding="utf-8")
            self.assertEqual(find_roi_click_tools(root), [expected.resolve()])

    def test_patch_restores_plugin_preferences_then_applies_optional_active_preset(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            toolset = Path(temp) / TOOLSET_NAME
            toolset.write_text(
                f"{HELPER_MARKER}\n\n{TOOL_MARKER}\n}}\n",
                encoding="utf-8",
            )
            backup = patch_roi_click_tools(toolset)
            self.assertIsNotNone(backup)
            text = toolset.read_text(encoding="utf-8")
            self.assertIn("function restoreSavedRoiClickSettings()", text)
            self.assertIn("function loadActiveRectPreset()", text)
            self.assertIn(PREFS_CALL, text)
            self.assertIn(PATCH_CALL, text)
            self.assertLess(text.index(PREFS_CALL), text.index(PATCH_CALL))
            for key in (
                "rect.width",
                "rect.height",
                "rect.angle",
                "default.addToManager",
                "default.runMeasure",
                "default.doNextSlice",
                "default.dimension",
                "default.doExtraCmd",
                "default.extraCmd",
            ):
                self.assertIn(key, text)

            second = patch_roi_click_tools(toolset)
            self.assertIsNone(second)
            self.assertEqual(toolset.read_text(encoding="utf-8"), text)

    def test_old_preset_only_patch_is_upgraded_without_duplicate_active_preset_function(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            toolset = Path(temp) / TOOLSET_NAME
            toolset.write_text(
                f"{HELPER_MARKER}\n\nfunction loadActiveRectPreset() {{\n}}\n\n{TOOL_MARKER}\n\n{PATCH_CALL}\n}}\n",
                encoding="utf-8",
            )
            patch_roi_click_tools(toolset)
            text = toolset.read_text(encoding="utf-8")
            self.assertEqual(text.count("function loadActiveRectPreset()"), 1)
            self.assertEqual(text.count("function restoreSavedRoiClickSettings()"), 1)
            self.assertEqual(text.count(PREFS_CALL), 1)
            self.assertEqual(text.count(PATCH_CALL), 1)

    def test_preset_values_must_be_finite_and_positive(self) -> None:
        self.assertEqual(
            validated_preset({"width": "108", "height": 120, "angle": "0"}),
            {"width": 108.0, "height": 120.0, "angle": 0.0},
        )
        for preset in (
            {"width": "NaN", "height": 120, "angle": 0},
            {"width": 108, "height": "inf", "angle": 0},
            {"width": 108, "height": 120, "angle": "NaN"},
            {"width": 0, "height": 120, "angle": 0},
            {"width": 108, "height": -1, "angle": 0},
        ):
            with self.subTest(preset=preset):
                with self.assertRaises(ValueError):
                    validated_preset(preset)


if __name__ == "__main__":
    unittest.main()
