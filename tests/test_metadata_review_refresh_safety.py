from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.reconcile_images_csv import FIELDS, read_previous_review, write_review


class MetadataReviewRefreshSafetyTests(unittest.TestCase):
    def test_changed_review_columns_are_rejected_before_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "images_reconciliation.csv"
            original = (
                "Filename,Folder,Experiment,Set,Type,MyNotes\n"
                "plate.jpg,setA,E1,A,YPDA,keep this\n"
            )
            path.write_text(original, encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                read_previous_review(path)

            self.assertIn("refusing to overwrite manual edits", str(caught.exception))
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_atomic_review_write_replaces_complete_file_and_leaves_no_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "images_reconciliation.csv"
            path.write_text("old incomplete contents\n", encoding="utf-8")
            rows = [
                {
                    "Filename": "plate.jpg",
                    "Folder": "setA",
                    "Experiment": "E1",
                    "Set": "A",
                    "Type": "YPDA",
                    "Status": "EXISTING",
                }
            ]

            write_review(path, rows)
            loaded = read_previous_review(path)

            self.assertEqual(loaded, rows)
            self.assertFalse(any(p.name.startswith(path.name + ".refresh-") for p in root.iterdir()))
            header = path.read_text(encoding="utf-8-sig").splitlines()[0]
            self.assertEqual(header.split(","), FIELDS)


if __name__ == "__main__":
    unittest.main()
