from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT_MACRO = REPO_ROOT / "fiji" / "full_column_alignment.ijm"


class AlignmentMacroContractTests(unittest.TestCase):
    def test_manual_authority_and_previous_roi_seed_contract_are_present(self) -> None:
        text = ALIGNMENT_MACRO.read_text(encoding="utf-8")

        self.assertIn('"1 / 2 — First column"', text)
        self.assertIn('"2 / 2 — Last column"', text)
        self.assertIn('Dialog.create("Alignment QC")', text)
        self.assertIn('context = argValue(arg, "context", "")', text)

        self.assertIn("seedPreviousReferenceROI", text)
        self.assertIn('"reference_roi_x="', text)
        self.assertIn('"reference_roi_y="', text)
        self.assertIn('"reference_roi_width="', text)
        self.assertIn('"reference_roi_height="', text)
        self.assertIn("it is NOT accepted automatically", text)

        self.assertIn("Array.findMaxima", text)
        self.assertIn("getProfile()", text)


if __name__ == "__main__":
    unittest.main()
