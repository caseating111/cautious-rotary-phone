from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import preflight_batch
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
            "crop_width": 130,
            "crop_height": 546,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def normalized_lines(self, lines: list[str]) -> list[str]:
        return [line.replace("\\", "/") for line in lines]

    def save_expected_png(self, path: Path, size: tuple[int, int] = (130, 546)) -> None:
        Image.new("L", size, 10).save(path)

    def expected_names(self) -> list[str]:
        meta = {"Experiment": "E1", "Set": "A", "Type": "YPDA"}
        grid_rows = [
            {"Column": "1", "Strain": "WT"},
            {"Column": "2", "Strain": "mut1"},
        ]
        return expected_output_names(meta, grid_rows)

    def test_preflight_semantic_validation_failure_is_blocking(self) -> None:
        validator = self.root / "validator.py"
        validator.write_text(
            "print('synthetic preflight metadata failure')\nraise SystemExit(1)\n",
            encoding="utf-8",
        )
        config = {
            "grid_csv": str(self.grid_csv),
            "images_csv": str(self.images_csv),
            "condition_order_csv": str(self.root / "condition_order.csv"),
        }
        with patch.object(preflight_batch, "VALIDATOR", validator):
            with self.assertRaises(SystemExit) as caught:
                preflight_batch.validate_project_csvs(config)
        self.assertIn("synthetic preflight metadata failure", str(caught.exception))

    def test_crop_output_cannot_live_inside_source_image_tree(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            preflight_batch.validate_output_layout(self.image_root, self.image_root / "derived")
        self.assertIn("crop_output must be outside image_root", str(caught.exception))
        preflight_batch.validate_output_layout(self.image_root, self.crop_root)

    def test_missing_outputs_leave_image_pending(self) -> None:
        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("Images still requiring batch work: 1", lines)
        self.assertIn("Crops still to produce/rebuild: 4", lines)

    def test_valid_csv_row_without_physical_image_is_expected_not_present_and_non_blocking(self) -> None:
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            "plate2.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )

        lines, problems, pending = build_report(self.config)

        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("Expected images not physically present: 1", lines)
        self.assertIn("EXPECTED IMAGES NOT PHYSICALLY PRESENT — NON-BLOCKING (1)", lines)
        self.assertIn("- plate2.jpg", lines)
        self.assertIn("STATUS: READY FOR BATCH ALIGNMENT", lines)

    def test_exact_existing_outputs_mark_image_complete(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        source_mtime = (self.source_folder / "plate1.jpg").stat().st_mtime_ns
        for index, name in enumerate(self.expected_names(), 1):
            path = output_dir / name
            self.save_expected_png(path)
            os.utime(path, ns=(source_mtime + index, source_mtime + index))

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual(pending, [])
        self.assertIn("Already complete images: 1", lines)
        self.assertIn("Crops still to produce/rebuild: 0", lines)

    def test_rotated_existing_outputs_are_also_current(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        source_mtime = (self.source_folder / "plate1.jpg").stat().st_mtime_ns
        for index, name in enumerate(self.expected_names(), 1):
            path = output_dir / name
            self.save_expected_png(path, (546, 130))
            os.utime(path, ns=(source_mtime + index, source_mtime + index))

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual(pending, [])
        self.assertIn("Already complete images: 1", lines)

    def test_wrong_dimension_expected_crop_marks_plate_pending(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        source_mtime = (self.source_folder / "plate1.jpg").stat().st_mtime_ns
        for index, name in enumerate(self.expected_names(), 1):
            path = output_dir / name
            self.save_expected_png(path, (130, 546) if index > 1 else (100, 100))
            os.utime(path, ns=(source_mtime + index, source_mtime + index))

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("INCOMPATIBLE EXPECTED CROPS — WILL REBUILD (1)", lines)
        self.assertIn("Crops still to produce/rebuild: 1", lines)

    def test_source_newer_than_existing_outputs_marks_plate_pending_for_rebuild(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        for name in self.expected_names():
            self.save_expected_png(output_dir / name)

        source = self.source_folder / "plate1.jpg"
        future = max(source.stat().st_mtime_ns, *(p.stat().st_mtime_ns for p in output_dir.iterdir())) + 10_000_000_000
        os.utime(source, ns=(future, future))

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("Already complete images: 0", lines)
        self.assertIn("Crops still to produce/rebuild: 4", lines)
        self.assertIn("STALE EXPECTED CROPS — WILL REBUILD (4)", lines)

    def test_partially_complete_plate_warns_about_whole_plate_rerun_without_blocking(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        existing = output_dir / self.expected_names()[0]
        self.save_expected_png(existing)
        source_mtime = (self.source_folder / "plate1.jpg").stat().st_mtime_ns
        os.utime(existing, ns=(source_mtime + 1, source_mtime + 1))

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("PARTIALLY COMPLETE PLATES — NON-BLOCKING (1)", lines)
        self.assertIn(
            "- setA/plate1.jpg: 1 current, 3 missing/stale/incompatible",
            self.normalized_lines(lines),
        )

    def test_unrelated_unexpected_crop_png_is_reported_but_not_blocking(self) -> None:
        output_dir = self.crop_root / "setA"
        output_dir.mkdir()
        (output_dir / "old_stale_crop.png").write_bytes(b"derived placeholder")

        lines, problems, pending = build_report(self.config)
        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("OTHER UNEXPECTED CROP PNGS — NON-BLOCKING (1)", lines)
        self.assertIn("- setA/old_stale_crop.png", self.normalized_lines(lines))

    def test_old_strain_suffix_crop_is_classified_as_superseded_non_blocking(self) -> None:
        output_dir = self.crop_root / "old"
        output_dir.mkdir()
        superseded = output_dir / "E1_A_YPDA_01_Top_OLD_STRAIN.png"
        self.save_expected_png(superseded, (546, 130))

        lines, problems, pending = build_report(self.config)

        self.assertFalse(problems)
        self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
        self.assertIn("SUPERSEDED PREFIX CROPS — NON-BLOCKING (1)", lines)
        self.assertIn("- old/E1_A_YPDA_01_Top_OLD_STRAIN.png", self.normalized_lines(lines))
        self.assertTrue(any("final Pillow jobs stage only exact current filenames" in line for line in lines))

    def test_semicolon_in_source_folder_is_blocking_before_fiji_handoff(self) -> None:
        unsafe = self.image_root / "set;unsafe"
        self.source_folder.rename(unsafe)
        self.source_folder = unsafe

        lines, problems, _ = build_report(self.config)
        self.assertTrue(problems)
        self.assertIn("SOURCE FOLDERS UNSAFE FOR FIJI ARGUMENT HANDOFF (1)", lines)
        self.assertIn("- set;unsafe", lines)

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
        self.assertIn("OUTPUT PATH COLLISIONS (WINDOWS CASE-INSENSITIVE) (4)", lines)
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
        self.assertNotIn("OUTPUT PATH COLLISIONS (WINDOWS CASE-INSENSITIVE) (4)", lines)
        self.assertIn("DOWNSTREAM CROP-NAME AMBIGUITIES (4)", lines)
        normalized = self.normalized_lines(lines)
        self.assertTrue(any("setA/plate1.jpg" in line and "setB/plate2.jpg" in line for line in normalized))

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
