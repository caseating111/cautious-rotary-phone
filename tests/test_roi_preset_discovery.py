from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.roi_preset_gui import TOOLSET_NAME, configured_fiji_root, find_roi_click_tools


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


if __name__ == "__main__":
    unittest.main()
