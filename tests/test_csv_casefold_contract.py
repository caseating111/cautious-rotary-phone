from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.validate_project_csvs import validate


class CsvCasefoldContractTests(unittest.TestCase):
    def write_project(self, root: Path, grid: str, images: str, conditions: str) -> tuple[Path, Path, Path]:
        grid_path = root / "grid.csv"
        images_path = root / "images.csv"
        conditions_path = root / "condition_order.csv"
        grid_path.write_text(grid, encoding="utf-8")
        images_path.write_text(images, encoding="utf-8")
        conditions_path.write_text(conditions, encoding="utf-8")
        return grid_path, images_path, conditions_path

    def test_case_only_experiment_set_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(
                Path(temp),
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,1,1,WT\n"
                "e1,A,1,1,mut1\n",
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n"
                "plate2.jpg,e1,A,SALT\n",
                "Order,Type\n1,YPDA\n2,SALT\n",
            )
            problems = validate(*paths)
            self.assertTrue(any("case-insensitive Experiment/Set collision" in item for item in problems))

    def test_case_only_condition_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(
                Path(temp),
                "Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,WT\n",
                "Filename,Experiment,Set,Type\nplate1.jpg,E1,A,YPDA\n",
                "Order,Type\n1,YPDA\n2,ypda\n",
            )
            problems = validate(*paths)
            self.assertTrue(any("case-insensitive Type collision" in item for item in problems))

    def test_underscore_boundary_collision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(
                Path(temp),
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A_B,1,1,WT\n"
                "E1_A,B,1,1,mut1\n",
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A_B,YPDA\n",
                "Order,Type\n1,YPDA\n",
            )
            problems = validate(*paths)
            self.assertTrue(any("ambiguous Pillow lookup prefix" in item for item in problems))
            self.assertTrue(any("E1/A_B/YPDA" in item and "E1_A/B/YPDA" in item for item in problems))

    def test_unambiguous_underscores_remain_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(
                Path(temp),
                "Experiment,Set,GridCols,Column,Strain\n"
                "EXP_1,SET_A,1,1,WT\n",
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,EXP_1,SET_A,YPDA_CONTROL\n",
                "Order,Type\n1,YPDA_CONTROL\n",
            )
            self.assertEqual(validate(*paths), [])

    def test_distinct_identifiers_remain_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(
                Path(temp),
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,1,1,WT\n"
                "E2,A,1,1,mut1\n",
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n"
                "plate2.jpg,E2,A,SALT\n",
                "Order,Type\n1,YPDA\n2,SALT\n",
            )
            self.assertEqual(validate(*paths), [])


if __name__ == "__main__":
    unittest.main()
