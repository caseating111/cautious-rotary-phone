from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.finalize_images_reconciliation import candidate_rows
from tools.reconcile_images_csv import build_rows


class MetadataReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_root = self.root / "images"
        (self.image_root / "folderA").mkdir(parents=True)
        (self.image_root / "folderA" / "known.jpg").write_bytes(b"placeholder")
        (self.image_root / "folderA" / "new.jpg").write_bytes(b"placeholder")
        self.images_csv = self.root / "images.csv"
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "known.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )
        self.config = {
            "image_root": str(self.image_root),
            "images_csv": str(self.images_csv),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_existing_metadata_is_preserved_and_new_source_blank(self) -> None:
        rows, counts = build_rows(self.config)
        by_name = {row["Filename"]: row for row in rows}
        self.assertEqual(by_name["known.jpg"]["Experiment"], "E1")
        self.assertEqual(by_name["known.jpg"]["Status"], "EXISTING")
        self.assertEqual(by_name["new.jpg"]["Experiment"], "")
        self.assertEqual(by_name["new.jpg"]["Status"], "NEW_SOURCE_NEEDS_METADATA")
        self.assertEqual(counts["EXISTING"], 1)

    def test_draft_metadata_survives_rescan(self) -> None:
        draft = [
            {
                "Filename": "new.jpg",
                "Folder": "folderA",
                "Experiment": "E1",
                "Set": "A",
                "Type": "SALT",
                "Status": "NEW_SOURCE_NEEDS_METADATA",
            }
        ]
        rows, _ = build_rows(self.config, draft)
        by_name = {row["Filename"]: row for row in rows}
        self.assertEqual(by_name["new.jpg"]["Type"], "SALT")
        self.assertEqual(by_name["new.jpg"]["Status"], "DRAFT_METADATA_READY")

    def test_candidate_uses_current_source_rows_only(self) -> None:
        review = [
            {
                "Filename": "known.jpg",
                "Folder": "folderA",
                "Experiment": "E1",
                "Set": "A",
                "Type": "YPDA",
                "Status": "EXISTING",
            },
            {
                "Filename": "old.jpg",
                "Folder": "",
                "Experiment": "E0",
                "Set": "Z",
                "Type": "OLD",
                "Status": "CSV_ROW_SOURCE_NOT_FOUND",
            },
        ]
        rows = candidate_rows(review)
        self.assertEqual(rows, [{"Filename": "known.jpg", "Experiment": "E1", "Set": "A", "Type": "YPDA"}])

    def test_candidate_rejects_incomplete_metadata(self) -> None:
        review = [
            {
                "Filename": "new.jpg",
                "Folder": "folderA",
                "Experiment": "",
                "Set": "A",
                "Type": "YPDA",
                "Status": "NEW_SOURCE_NEEDS_METADATA",
            }
        ]
        with self.assertRaises(SystemExit):
            candidate_rows(review)


    def test_source_and_authoritative_filename_match_case_insensitively(self) -> None:
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\nKNOWN.JPG,E1,A,YPDA\n",
            encoding="utf-8",
        )
        rows, _ = build_rows(self.config)
        known = next(row for row in rows if row["Filename"] == "known.jpg")
        self.assertEqual(known["Status"], "EXISTING")
        self.assertEqual(known["Experiment"], "E1")

    def test_candidate_rejects_case_only_duplicate_basenames(self) -> None:
        review = [
            {"Filename": name, "Folder": folder, "Experiment": "E1", "Set": "A", "Type": "YPDA", "Status": "EXISTING"}
            for name, folder in (("Plate.JPG", "A"), ("plate.jpg", "B"))
        ]
        with self.assertRaises(SystemExit) as caught:
            candidate_rows(review)
        self.assertIn("Duplicate source basenames", str(caught.exception))
if __name__ == "__main__":
    unittest.main()
