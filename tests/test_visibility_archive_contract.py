from __future__ import annotations

import unittest
from pathlib import Path

from tools import run_fiji_macro_from_config as launcher


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "fiji" / "apply_global_visibility_and_archive.ijm"
INNER = REPO_ROOT / "fiji" / "apply_global_visibility.ijm"


class VisibilityArchiveContractTests(unittest.TestCase):
    def test_launcher_uses_archive_wrapper_around_unchanged_visibility_calculation(self) -> None:
        self.assertEqual(launcher.VISIBILITY_MACRO, WRAPPER)
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn('inner = macroDir + "apply_global_visibility.ijm";', text)
        self.assertIn("runMacro(inner, getArgument());", text)
        self.assertTrue(INNER.is_file())

    def test_archive_captures_source_identity_and_range_in_backend_folder(self) -> None:
        text = WRAPPER.read_text(encoding="utf-8")
        self.assertIn('sourceDirectory = getInfo("image.directory")', text)
        self.assertIn('sourceFilename = getInfo("image.filename")', text)
        self.assertIn('"display-ranges"', text)
        self.assertIn('"source_directory=" + sourceDirectory', text)
        self.assertIn('"source_filename=" + sourceFilename', text)
        self.assertIn("lastText", text)
        self.assertIn('readValue(lastText, "source", "") != sourceTitle', text)


if __name__ == "__main__":
    unittest.main()
