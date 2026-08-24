from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.run_existing_pillow_from_config import validate_unique_crop_matches


class PillowInputCompletenessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.crop_root = self.root / "crops"
        self.crop_root.mkdir()
        self.grid_csv = self.root / "grid.csv"
        self.images_csv = self.root / "images.csv"
        self.grid_csv.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,1,1,WT\n",
            encoding="utf-8",
        )
        self.images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_expected_crop_is_blocking_by_default(self) -> None:
        Image.new("L", (546, 130), 10).save(self.crop_root / "E1_A_YPDA_01_Top_WT.png")

        with self.assertRaises(SystemExit) as caught:
            validate_unique_crop_matches(self.crop_root, self.grid_csv, self.images_csv)

        message = str(caught.exception)
        self.assertIn("Incomplete crop inputs", message)
        self.assertIn("e1_a_ypda_01_low_", message)



if __name__ == "__main__":
    unittest.main()
