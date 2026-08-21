from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MACRO = REPO_ROOT / "existing scripts clean" / "roibox RUN ALL IN PARENT.ijm"


class PendingSkipBeforeOpenTests(unittest.TestCase):
    def test_metadata_lookup_and_absent_skip_happen_before_image_open(self) -> None:
        text = SOURCE_MACRO.read_text(encoding="utf-8")

        lookup = text.index('quotedPrefix = "\\\"" + fileName + "\\\",";')
        absent = text.index('if (experiment == "")', lookup)
        open_image = text.index("open(fullPath);", absent)

        self.assertLess(lookup, absent)
        self.assertLess(absent, open_image)
        self.assertIn("continue;", text[absent:open_image])
        self.assertNotIn("close();", text[absent:open_image])
        self.assertIn('plainPrefix  = fileName + ",";', text[lookup:absent])
        self.assertIn("notListedImages++;", text[absent:open_image])
        self.assertNotIn("skippedImages++;", text[absent:open_image])

    def test_old_post_open_title_lookup_is_not_reintroduced(self) -> None:
        text = SOURCE_MACRO.read_text(encoding="utf-8")
        open_image = text.index("open(fullPath);")
        source_title = text.index("sourceTitle = getTitle();", open_image)

        self.assertLess(open_image, source_title)
        self.assertNotIn('quotedPrefix = "\\\"" + sourceTitle', text)
        self.assertNotIn('plainPrefix  = sourceTitle + ",";', text)

    def test_final_summary_distinguishes_not_pending_from_real_skips(self) -> None:
        text = SOURCE_MACRO.read_text(encoding="utf-8")
        self.assertIn('"Not listed / not pending: " + notListedImages', text)
        self.assertIn('"Skipped after metadata match: " + skippedImages', text)


if __name__ == "__main__":
    unittest.main()
