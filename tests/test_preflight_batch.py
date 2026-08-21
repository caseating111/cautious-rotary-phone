from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.preflight_batch import build_report, expected_output_names


class PreflightBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_root = self.root / "images"
        self.crop_root = self.root / "crops"
        self.source_folder = self.image_root / "setA"
        self.source_folder.mkdir(parents=True)
        self.crop_root.mkdir()
        (self.source_folder / "plate1.jpg").write_bytes(b"synthetic placeholder")

        self.grid_csv = self.root / "grid.csv"
        self.images_csv = self.root / "images.csv"
        self.grid_csv.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,2,1,WT\n"
            "E1,A,2,2,mut1\n",
            encoding="utf-8",
        )
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )
        self.config = {
            "image_root": str(self.image_root),
            "crop_output": str(self.crop_root),
            "grid_csv": str(self.grid_csv),
            "images_csv": str(self.images_csv),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_outputs_leave_image_pending(self) -> None:
        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("Images still requiring batch work: 1", lines)
        self.assertIn("Crops still to produce: 4", lines)

    def test_exact_existing_outputs_mark_image_complete(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        meta = {"Experiment": "E1", "Set": "A", "Type": "YPDA"}
        grid_rows = [
            {"Column": "1", "Strain": "WT"},
            {"Column": "2", "Strain": "mut1"},
        ]
        for name in expected_output_names(meta, grid_rows):
            (output_dir / name).write_bytes(b"derived placeholder")

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual(pending, [])
        self.assertIn("Already complete images: 1", lines)
        self.assertIn("Crops still to produce: 0", lines)

    def test_duplicate_source_basename_is_blocking(self) -> None:
        second_folder = self.image_root / "setB"
        second_folder.mkdir()
        (second_folder / "plate1.jpg").write_bytes(b"synthetic placeholder")

        lines, problems, _ = build_report(self.config)
        self.assertTrue(problems)
        self.assertIn("DUPLICATE SOURCE BASENAMES (1)", lines)

    def test_two_images_cannot_claim_same_output_names_in_one_folder(self) -> None:
        (self.source_folder / "plate2.jpg").write_bytes(b"synthetic placeholder")
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            "plate2.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )

        lines, problems, _ = build_report(self.config)
        self.assertTrue(problems)
        self.assertIn("OUTPUT FILENAME COLLISIONS (4)", lines)
        self.assertTrue(any("plate1.jpg" in line and "plate2.jpg" in line for line in lines))

    def test_same_metadata_in_different_source_folders_is_downstream_ambiguous(self) -> None:
        second_folder = self.image_root / "setB"
        second_folder.mkdir()
        (second_folder / "plate2.jpg").write_bytes(b"synthetic placeholder")
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            "plate2.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )

        lines, problems, pending = build_report(self.config)
        self.assertTrue(problems)
        self.assertEqual(sorted(row["Filename"] for row in pending), ["plate1.jpg", "plate2.jpg"])
        self.assertNotIn("OUTPUT FILENAME COLLISIONS (4)", lines)
        self.assertIn("DOWNSTREAM CROP-NAME AMBIGUITIES (4)", lines)
        self.assertTrue(any("setA/plate1.jpg" in line and "setB/plate2.jpg" in line for line in lines))

    def test_distinct_type_in_different_source_folder_remains_unambiguous(self) -> None:
        second_folder = self.image_root / "setB"
        second_folder.mkdir()
        (second_folder / "plate2.jpg").write_bytes(b"synthetic placeholder")
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            "plate2.jpg,E1,A,SALT\n",
            encoding="utf-8",
        )

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual(sorted(row["Filename"] for row in pending), ["plate1.jpg", "plate2.jpg"])
        self.assertNotIn("DOWNSTREAM CROP-NAME AMBIGUITIES", lines)


if __name__ == "__main__":
    unittest.main()
