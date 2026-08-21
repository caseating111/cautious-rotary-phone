from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.metadata_review_gui import adopt_candidate, configured_images_csv, unique_backup_path


class MetadataCandidateAdoptionTests(unittest.TestCase):
    def test_configured_images_csv_reads_saved_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "metadata" / "images.csv"
            config = root / "config.json"
            config.write_text(json.dumps({"images_csv": str(destination)}), encoding="utf-8")
            self.assertEqual(configured_images_csv(config), destination)

    def test_adopt_candidate_backs_up_existing_authoritative_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "candidate.csv"
            destination = root / "project" / "images.csv"
            destination.parent.mkdir()
            candidate.write_text("new\n", encoding="utf-8")
            destination.write_text("old\n", encoding="utf-8")

            backup = adopt_candidate(candidate, destination)
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual(backup.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(destination.read_text(encoding="utf-8"), "new\n")

    def test_repeated_adoptions_use_distinct_backups(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "images.csv"
            destination.write_text("v1\n", encoding="utf-8")
            first = unique_backup_path(destination)
            first.write_text("backup\n", encoding="utf-8")
            second = unique_backup_path(destination)
            self.assertNotEqual(first, second)
            self.assertTrue(second.name.endswith(".before-reconciliation.1.bak"))

    def test_adopt_candidate_can_create_missing_authoritative_file_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "candidate.csv"
            destination = root / "new" / "images.csv"
            candidate.write_text("new\n", encoding="utf-8")
            backup = adopt_candidate(candidate, destination)
            self.assertIsNone(backup)
            self.assertEqual(destination.read_text(encoding="utf-8"), "new\n")


if __name__ == "__main__":
    unittest.main()
