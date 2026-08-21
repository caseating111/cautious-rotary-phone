from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools.project_layout import default_prefix, initialize_project, planned_layout, validate_prefix


class ProjectLayoutTests(unittest.TestCase):
    def test_default_prefix_is_dd_mm_yy_and_custom_text_is_allowed(self) -> None:
        self.assertEqual(default_prefix(date(2026, 8, 21)), "21.08.26")
        self.assertEqual(validate_prefix("ATTEMPT1"), "ATTEMPT1")
        with self.assertRaises(SystemExit):
            validate_prefix("BAD;NAME")

    def test_initialization_moves_source_folder_intact_and_creates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            source = parent / "MyImages"
            nested = source / "setA"
            nested.mkdir(parents=True)
            original = nested / "plate1.jpg"
            original.write_bytes(b"unchanged-image-bytes")

            layout = initialize_project(source, "21.08.26")

            self.assertEqual(layout.project_root, parent / "21.08.26_MyImages")
            self.assertEqual(layout.image_root, layout.project_root / "Raw" / "MyImages")
            self.assertFalse(source.exists())
            self.assertEqual((layout.image_root / "setA" / "plate1.jpg").read_bytes(), b"unchanged-image-bytes")
            self.assertTrue(layout.crop_output.is_dir())
            self.assertTrue(layout.matrix_output.is_dir())
            self.assertTrue(layout.metadata_dir.is_dir())

    def test_existing_raw_layout_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "ATTEMPT1_MyImages"
            image_root = project / "Raw" / "MyImages"
            image_root.mkdir(parents=True)

            layout = initialize_project(image_root, "IGNORED")

            self.assertEqual(layout.project_root, project)
            self.assertEqual(layout.image_root, image_root)
            self.assertTrue((project / "Crops").is_dir())
            self.assertTrue((project / "Matrices").is_dir())
            self.assertTrue((project / "Metadata").is_dir())

    def test_existing_target_project_is_never_merged_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            source = parent / "MyImages"
            source.mkdir()
            target = planned_layout(source, "21.08.26").project_root
            target.mkdir()
            (target / "keep.txt").write_text("existing", encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                initialize_project(source, "21.08.26")
            self.assertIn("refusing to merge", str(caught.exception))
            self.assertTrue(source.is_dir())
            self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "existing")


if __name__ == "__main__":
    unittest.main()
