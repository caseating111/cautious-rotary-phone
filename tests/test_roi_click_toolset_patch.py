from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import patch_roi_click_toolset as patcher


MINIMAL_UPSTREAM = '''// Global variables
var addToManager = true;
var runMeasure = true;
var doNextSlice = true;
var dimension = "time";
var doExtraCmd = false;
var extraCmd = "x";
var rotRectWidth = 100;
var rotRectHeight = 50;
var rotRectAngle = 0;
macro "Rotated Rectangle Click Tool - Cf00R11cc" {
	getCursorLoc(xcenter, ycenter, z, flags);
}
'''


class RoiClickToolsetPatchTests(unittest.TestCase):
    def test_patch_restores_specific_rectangle_and_shared_settings_each_click(self) -> None:
        patched, changed = patcher.patch_text(MINIMAL_UPSTREAM)
        self.assertTrue(changed)
        self.assertIn(patcher.PATCH_MARKER, patched)
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
            self.assertIn(key, patched)

        again, changed_again = patcher.patch_text(patched)
        self.assertFalse(changed_again)
        self.assertEqual(again, patched)

    def test_unknown_toolset_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            patcher.patch_text("macro \"Something Else\" {}\n")

    def test_install_creates_one_backup_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Fiji.app"
            fiji = root / "ImageJ-win64.exe"
            toolset_dir = root / "macros" / "toolsets"
            toolset_dir.mkdir(parents=True)
            fiji.write_text("stub", encoding="utf-8")
            toolset = toolset_dir / patcher.TOOLSET_NAME
            toolset.write_text(MINIMAL_UPSTREAM, encoding="utf-8")

            path, changed = patcher.ensure_patched(fiji)
            self.assertEqual(path, toolset)
            self.assertTrue(changed)
            backup = toolset.with_name(toolset.name + patcher.BACKUP_SUFFIX)
            self.assertEqual(backup.read_text(encoding="utf-8"), MINIMAL_UPSTREAM)
            self.assertIn(patcher.PATCH_MARKER, toolset.read_text(encoding="utf-8"))

            _, changed_again = patcher.ensure_patched(fiji)
            self.assertFalse(changed_again)
            self.assertEqual(backup.read_text(encoding="utf-8"), MINIMAL_UPSTREAM)


if __name__ == "__main__":
    unittest.main()
