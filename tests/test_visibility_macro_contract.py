from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VISIBILITY_MACRO = REPO_ROOT / "fiji" / "apply_global_visibility.ijm"


class VisibilityMacroContractTests(unittest.TestCase):
    def test_rgb_visibility_uses_disposable_qc_duplicate_before_display_range(self) -> None:
        text = VISIBILITY_MACRO.read_text(encoding="utf-8")

        depth_at = text.index("sourceDepth = bitDepth();")
        rgb_at = text.index("if (sourceDepth == 24)", depth_at)
        duplicate_at = text.index('run("Duplicate...", "title=QC_display");', rgb_at)
        convert_at = text.index('run("8-bit");', duplicate_at)
        minmax_at = text.index("setMinAndMax(blackPoint, highPoint);", convert_at)

        self.assertLess(rgb_at, duplicate_at)
        self.assertLess(duplicate_at, convert_at)
        self.assertLess(convert_at, minmax_at)
        self.assertNotIn('run("Apply LUT")', text)
        self.assertNotIn('run("Enhance Contrast"', text)

    def test_background_and_high_point_use_native_histogram_statistics(self) -> None:
        text = VISIBILITY_MACRO.read_text(encoding="utf-8")

        for side in ("topMedian", "bottomMedian", "leftMedian", "rightMedian"):
            self.assertIn(f"{side} = sampleRectPercentile", text)
        self.assertIn(
            "background = robustSideMedian(topMedian, bottomMedian, leftMedian, rightMedian);",
            text,
        )
        self.assertIn("highPoint = selectionPercentile(highPercent);", text)
        self.assertIn("getHistogram(values, counts, 256);", text)

    def test_saved_alignment_identity_is_checked_before_visibility_work(self) -> None:
        text = VISIBILITY_MACRO.read_text(encoding="utf-8")

        identity_at = text.index("alignmentMatchesCurrentImage(")
        depth_at = text.index("sourceDepth = bitDepth();")
        self.assertLess(identity_at, depth_at)
        self.assertIn('savedDirectory = readAlignmentValue(path, "source_directory", "");', text)
        self.assertIn('savedFilename = readAlignmentValue(path, "source_filename", "");', text)


if __name__ == "__main__":
    unittest.main()
