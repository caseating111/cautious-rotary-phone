from __future__ import annotations

import unittest

from tools import run_four_point_batch_from_config as batch


class FourPointMathematicalQCTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = batch.SOURCE_MACRO.read_text(encoding="utf-8")

    def test_enhanced_route_preserves_four_anchor_geometry_and_fixed_crop_export(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        for label in ("R1C1", "R1C\" + gridCols", "R5C1", "R5C\" + gridCols"):
            self.assertIn(label, text)
        self.assertIn("TOP_FACTOR = 0.375;", text)
        self.assertIn("LOW_FACTOR = 1.375;", text)
        self.assertIn("CROP_W", text)
        self.assertIn("CROP_H", text)

    def test_alignment_view_is_disposable_and_uses_whole_image_double_clahe(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        self.assertIn('run("Duplicate...", "title=__alignment_view__")', text)
        self.assertIn('run("Select None")', text)
        self.assertEqual(text.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
        self.assertNotIn("sampleW =", text)
        self.assertNotIn('run("Enhance Contrast", "saturated=0.35")', text)
        self.assertIn('selectWindow(sourceTitle);', text)

    def test_full_grid_qc_is_pure_math_and_runs_before_export(self) -> None:
        text = batch.enhance_four_point_macro(self.source)
        qc = text.index('Dialog.create("Full-grid QC")')
        export = text.index("// EXPORT CROPS", qc)
        self.assertLess(qc, export)
        self.assertIn("for (qcRow = 1; qcRow <= 8; qcRow++)", text)
        self.assertIn("for (qcCol = 1; qcCol <= gridCols; qcCol++)", text)
        self.assertIn("v = (qcRow - 1) / 4;", text)
        self.assertIn("u = (qcCol - 1) / (gridCols - 1);", text)
        self.assertIn('newArray("Accept", "Retry")', text)
        self.assertNotIn("Array.findMaxima", text)
        self.assertNotIn("getProfile()", text)


if __name__ == "__main__":
    unittest.main()
