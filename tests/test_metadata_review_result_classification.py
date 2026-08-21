from __future__ import annotations

import inspect
import unittest

from tools.metadata_review_gui import MetadataReview, reconciliation_result_is_expected


class MetadataReviewResultClassificationTests(unittest.TestCase):
    def test_success_is_expected(self) -> None:
        self.assertTrue(reconciliation_result_is_expected(0, "Metadata reconciliation written: x"))

    def test_written_review_with_blocking_rows_is_expected(self) -> None:
        output = "Metadata reconciliation written: review.csv\nNEW_SOURCE_NEEDS_METADATA: 2"
        self.assertTrue(reconciliation_result_is_expected(1, output))

    def test_fatal_code_one_without_written_marker_is_not_expected(self) -> None:
        output = "Existing reconciliation review columns changed; refusing to overwrite manual edits."
        self.assertFalse(reconciliation_result_is_expected(1, output))

    def test_other_nonzero_code_is_not_expected(self) -> None:
        self.assertFalse(reconciliation_result_is_expected(2, "fatal"))

    def test_reconcile_only_opens_review_after_expected_result(self) -> None:
        source = inspect.getsource(MetadataReview.reconcile)
        expected_at = source.index("expected = reconciliation_result_is_expected")
        guarded_open_at = source.index("if expected and REVIEW.is_file()", expected_at)
        error_at = source.index("if not expected:", guarded_open_at)
        self.assertLess(expected_at, guarded_open_at)
        self.assertLess(guarded_open_at, error_at)


if __name__ == "__main__":
    unittest.main()
