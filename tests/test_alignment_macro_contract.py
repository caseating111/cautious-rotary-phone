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

    def test_profile_fallback_uses_native_roi_statistics_not_custom_pixel_reads(self) -> None:
        text = ALIGNMENT_MACRO.read_text(encoding="utf-8")
        fallback_at = text.index("function getVerticalAverageProfileFallback")
        fallback_block = text[fallback_at : text.index("function findExpectedPeaks", fallback_at)]

        self.assertIn("makeRectangle(x, y + yy, w, 1);", fallback_block)
        self.assertIn("getStatistics(area, mean);", fallback_block)
        self.assertIn("profile[yy] = mean;", fallback_block)
        self.assertIn("makeRectangle(x, y, w, h);", fallback_block)
        self.assertNotIn("getValue(", fallback_block)
        self.assertNotIn("getPixel(", fallback_block)

    def test_previous_span_only_prepositions_last_roi_before_manual_confirmation(self) -> None:
        text = ALIGNMENT_MACRO.read_text(encoding="utf-8")
        first_bounds_at = text.index("getSelectionBounds(lx, ly, lw, lh);")
        span_seed_at = text.index("suggestedX = lx + previousColumnSpan;", first_bounds_at)
        move_at = text.index("makeRectangle(suggestedX, ly, lw, lh);", span_seed_at)
        last_wait_at = text.index('"2 / 2 — Last column"', move_at)
        right_bounds_at = text.index("getSelectionBounds(rx, ry, rw, rh);", last_wait_at)

        self.assertIn("readPreviousColumnSpan(sourceWidth, sourceHeight)", text)
        self.assertIn("previousRightX <= previousLeftX", text)
        self.assertLess(first_bounds_at, span_seed_at)
        self.assertLess(span_seed_at, move_at)
        self.assertLess(move_at, last_wait_at)
        self.assertLess(last_wait_at, right_bounds_at)
        self.assertIn("Fine-tune it for this plate; it is NOT accepted automatically.", text)
        self.assertIn("Press OK (or Z) when positioned.", text[last_wait_at:right_bounds_at])

    def test_last_stage_retries_restore_current_first_roi(self) -> None:
        text = ALIGNMENT_MACRO.read_text(encoding="utf-8")
        restore = "makeRectangle(lx, ly, lw, lh);"

        last_invalid_at = text.index('showMessage("Last-column ROI"')
        last_profile_at = text.index('showMessage("Last-column profile"')
        qc_retry_at = text.index("} else {", text.index('if (action == "Accept")'))

        self.assertIn(restore, text[last_invalid_at : text.index("continue;", last_invalid_at)])
        self.assertIn(restore, text[last_profile_at : text.index("continue;", last_profile_at)])
        self.assertIn(restore, text[qc_retry_at : text.index("}\n}", qc_retry_at)])

    def test_alignment_is_persisted_only_after_explicit_qc_accept(self) -> None:
        text = ALIGNMENT_MACRO.read_text(encoding="utf-8")
        qc_at = text.index('Dialog.create("Alignment QC")')
        accept_at = text.index('if (action == "Accept")', qc_at)
        save_at = text.index("saveLastAlignment(", accept_at)
        retry_at = text.index("} else {", save_at)
        retry_block = text[retry_at : text.index("}\n}", retry_at) + 2]

        self.assertLess(qc_at, accept_at)
        self.assertLess(accept_at, save_at)
        self.assertIn("accepted = 1;", text[accept_at:save_at])
        self.assertIn("Overlay.remove;", retry_block)
        self.assertIn("makeRectangle(lx, ly, lw, lh);", retry_block)
        self.assertNotIn("saveLastAlignment(", retry_block)


if __name__ == "__main__":
    unittest.main()
