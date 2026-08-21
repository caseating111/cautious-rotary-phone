from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.validate_project_csvs import validate


class CsvValidationTests(unittest.TestCase):
    def write_project(self, grid: str, images: str, conditions: str) -> tuple[Path, Path, Path, tempfile.TemporaryDirectory]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        grid_path = root / "grid.csv"
        images_path = root / "images.csv"
        conditions_path = root / "condition_order.csv"
        grid_path.write_text(grid, encoding="utf-8")
        images_path.write_text(images, encoding="utf-8")
        conditions_path.write_text(conditions, encoding="utf-8")
        return grid_path, images_path, conditions_path, temp

    def test_quoted_comma_in_strain_is_rejected_for_imagej_handoff(self) -> None:
        paths = self.write_project(
            'Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,"strain,alpha"\n',
            'Filename,Experiment,Set,Type\nplate1.jpg,E1,A,YPDA\n',
            'Order,Type\n1,YPDA\n',
        )
        grid, images, conditions, temp = paths
        try:
            problems = validate(grid, images, conditions)
        finally:
            temp.cleanup()
        self.assertTrue(any("Strain contains a comma" in problem for problem in problems))

    def test_comma_in_filename_remains_supported(self) -> None:
        paths = self.write_project(
            'Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,WT\n',
            'Filename,Experiment,Set,Type\n"plate,1.jpg",E1,A,YPDA\n',
            'Order,Type\n1,YPDA\n',
        )
        grid, images, conditions, temp = paths
        try:
            problems = validate(grid, images, conditions)
        finally:
            temp.cleanup()
        self.assertEqual(problems, [])

    def test_comma_in_image_metadata_is_rejected(self) -> None:
        paths = self.write_project(
            'Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,WT\n',
            'Filename,Experiment,Set,Type\nplate1.jpg,E1,A,"YPDA,plus"\n',
            'Order,Type\n1,"YPDA,plus"\n',
        )
        grid, images, conditions, temp = paths
        try:
            problems = validate(grid, images, conditions)
        finally:
            temp.cleanup()
        self.assertTrue(any("Type contains a comma" in problem for problem in problems))

    def test_semicolon_in_macro_argument_metadata_is_rejected(self) -> None:
        paths = self.write_project(
            'Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,WT\n',
            'Filename,Experiment,Set,Type\nplate1.jpg,E1,A,"YPDA;plus"\n',
            'Order,Type\n1,"YPDA;plus"\n',
        )
        grid, images, conditions, temp = paths
        try:
            problems = validate(grid, images, conditions)
        finally:
            temp.cleanup()
        self.assertTrue(any("Type contains a semicolon" in problem for problem in problems))

    def test_line_break_in_imagej_line_metadata_is_rejected(self) -> None:
        paths = self.write_project(
            'Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,"strain\nalpha"\n',
            'Filename,Experiment,Set,Type\nplate1.jpg,E1,A,YPDA\n',
            'Order,Type\n1,YPDA\n',
        )
        grid, images, conditions, temp = paths
        try:
            problems = validate(grid, images, conditions)
        finally:
            temp.cleanup()
        self.assertTrue(any("Strain contains a line break" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
