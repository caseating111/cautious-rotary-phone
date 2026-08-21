from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.project_csv_discovery import discover_project_csvs


class ProjectCsvDiscoveryTests(unittest.TestCase):
    def test_finds_case_insensitive_dated_csv_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            grid = folder / "15.01.21 GRID.CSV"
            images = folder / "attempt 2 Images.csv"
            conditions = folder / "OLD_condition_order.CsV"
            for path in (grid, images, conditions):
                path.write_text("placeholder\n", encoding="utf-8")

            found = discover_project_csvs(folder)

            self.assertEqual(found["grid_csv"], grid.resolve())
            self.assertEqual(found["images_csv"], images.resolve())
            self.assertEqual(found["condition_order_csv"], conditions.resolve())

    def test_exact_filename_wins_over_other_substring_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            exact_grid = folder / "GRID.csv"
            old_grid = folder / "15.01.21 grid.csv"
            images = folder / "images.csv"
            conditions = folder / "condition_order.csv"
            for path in (exact_grid, old_grid, images, conditions):
                path.write_text("placeholder\n", encoding="utf-8")

            found = discover_project_csvs(folder)

            self.assertEqual(found["grid_csv"], exact_grid.resolve())

    def test_ambiguous_substring_matches_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "15.01.21 grid.csv").write_text("x\n", encoding="utf-8")
            (folder / "20.02.21 grid.csv").write_text("x\n", encoding="utf-8")
            (folder / "images.csv").write_text("x\n", encoding="utf-8")
            (folder / "condition_order.csv").write_text("x\n", encoding="utf-8")

            with self.assertRaises(ValueError) as caught:
                discover_project_csvs(folder)

            self.assertIn("More than one CSV matches 'grid.csv'", str(caught.exception))
            self.assertIn("15.01.21 grid.csv", str(caught.exception))
            self.assertIn("20.02.21 grid.csv", str(caught.exception))

    def test_missing_required_match_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "grid.csv").write_text("x\n", encoding="utf-8")
            (folder / "images.csv").write_text("x\n", encoding="utf-8")

            with self.assertRaises(ValueError) as caught:
                discover_project_csvs(folder)

            self.assertIn("condition_order.csv", str(caught.exception))

    def test_non_csv_files_are_not_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "grid.csv.backup").write_text("x\n", encoding="utf-8")
            (folder / "images.csv").write_text("x\n", encoding="utf-8")
            (folder / "condition_order.csv").write_text("x\n", encoding="utf-8")

            with self.assertRaises(ValueError) as caught:
                discover_project_csvs(folder)

            self.assertIn("grid.csv", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
