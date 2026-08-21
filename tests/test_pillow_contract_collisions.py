from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.run_existing_pillow_from_config import expected_crop_contract


class PillowContractCollisionTests(unittest.TestCase):
    def write_project(self, root: Path, second_experiment: str) -> tuple[Path, Path]:
        grid = root / "grid.csv"
        grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,1,1,WT\n"
            f"{second_experiment},A,1,1,WT\n",
            encoding="utf-8",
        )
        images = root / "images.csv"
        images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            f"plate2.jpg,{second_experiment},A,YPDA\n",
            encoding="utf-8",
        )
        return grid, images

    def test_case_only_duplicate_staged_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            grid, images = self.write_project(Path(temp), second_experiment="e1")

            with self.assertRaises(SystemExit) as caught:
                expected_crop_contract(grid, images)

            message = str(caught.exception)
            self.assertIn("Duplicate logical crop identity", message)
            self.assertIn("plate1.jpg", message)
            self.assertIn("plate2.jpg", message)
            self.assertIn("e1_a_ypda_01_top_", message)

    def test_identical_metadata_from_two_images_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            grid = root / "grid.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\nE1,A,1,1,WT\n",
                encoding="utf-8",
            )
            images = root / "images.csv"
            images.write_text(
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n"
                "plate2.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as caught:
                expected_crop_contract(grid, images)

            self.assertIn("Duplicate logical crop identity", str(caught.exception))

    def test_distinct_staged_identities_remain_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            grid, images = self.write_project(Path(temp), second_experiment="E2")

            contract = expected_crop_contract(grid, images)

            self.assertEqual(len(contract), 4)
            self.assertIn("e1_a_ypda_01_top_", contract)
            self.assertIn("e2_a_ypda_01_top_", contract)


if __name__ == "__main__":
    unittest.main()
