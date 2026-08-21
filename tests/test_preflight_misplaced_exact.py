from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.preflight_batch import build_report


class MisplacedExactCropPreflightTests(unittest.TestCase):
    def test_exact_current_crop_name_in_wrong_folder_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = root / "images"
            source_folder = image_root / "setA"
            crop_root = root / "crops"
            wrong_folder = crop_root / "old"
            source_folder.mkdir(parents=True)
            wrong_folder.mkdir(parents=True)
            Image.new("L", (200, 200), 10).save(source_folder / "plate1.jpg")

            grid_csv = root / "grid.csv"
            images_csv = root / "images.csv"
            grid_csv.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,2,1,WT\n"
                "E1,A,2,2,mut1\n",
                encoding="utf-8",
            )
            images_csv.write_text(
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )

            misplaced = wrong_folder / "E1_A_YPDA_01_Top_WT.png"
            Image.new("L", (130, 546), 20).save(misplaced)

            lines, problems, pending = build_report(
                {
                    "image_root": str(image_root),
                    "crop_output": str(crop_root),
                    "grid_csv": str(grid_csv),
                    "images_csv": str(images_csv),
                    "crop_width": 130,
                    "crop_height": 546,
                }
            )

            self.assertTrue(problems)
            self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
            self.assertIn("EXACT CURRENT CROP IN UNEXPECTED FOLDER (1)", lines)
            self.assertIn("- old/E1_A_YPDA_01_Top_WT.png", lines)
            self.assertTrue(any("final Pillow staging would correctly reject the duplicate" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
