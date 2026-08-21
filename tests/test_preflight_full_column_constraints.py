from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.preflight_batch import build_report


class FullColumnPreflightConstraintTests(unittest.TestCase):
    def test_one_column_grid_is_blocked_for_full_column_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_root = root / "images"
            source_folder = image_root / "setA"
            crop_root = root / "crops"
            source_folder.mkdir(parents=True)
            crop_root.mkdir()
            (source_folder / "plate1.jpg").write_bytes(b"synthetic placeholder")

            grid_csv = root / "grid.csv"
            images_csv = root / "images.csv"
            grid_csv.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,1,1,WT\n",
                encoding="utf-8",
            )
            images_csv.write_text(
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )

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
            self.assertIn("GRIDS UNSUPPORTED BY FULL-COLUMN ALIGNMENT (1)", lines)
            self.assertIn("- E1/A: GridCols=1", lines)


if __name__ == "__main__":
    unittest.main()
