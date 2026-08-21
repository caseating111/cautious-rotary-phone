from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import run_existing_pillow_from_config as pillow_adapter


class LegacyMatrixEndToEndTests(unittest.TestCase):
    def test_configured_legacy_matrix_script_builds_top_and_low_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop_root = root / "crops"
            crop_folder = crop_root / "setA"
            matrix_root = root / "matrices"
            crop_folder.mkdir(parents=True)
            matrix_root.mkdir()

            grid_csv = root / "grid.csv"
            images_csv = root / "images.csv"
            conditions_csv = root / "condition_order.csv"
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
            conditions_csv.write_text("Order,Type\n1,YPDA\n", encoding="utf-8")

            for column, strain in ((1, "WT"), (2, "mut1")):
                for state in ("Top", "Low"):
                    path = crop_folder / f"E1_A_YPDA_{column:02d}_{state}_{strain}.png"
                    Image.new("L", (48, 20), 30 + column).save(path)

            config = {
                "crop_output": str(crop_root),
                "matrix_output": str(matrix_root),
                "grid_csv": str(grid_csv),
                "images_csv": str(images_csv),
                "condition_order_csv": str(conditions_csv),
            }
            with patch.object(pillow_adapter, "APP_DIR", root / "configured"):
                configured = pillow_adapter.configured_copy("matrices", config)

            result = subprocess.run(
                [sys.executable, str(configured)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            output = matrix_root / "EXP"
            top = output / "E1_A_Top_MATRIX.png"
            low = output / "E1_A_Low_MATRIX.png"
            self.assertTrue(top.is_file(), result.stdout + result.stderr)
            self.assertTrue(low.is_file(), result.stdout + result.stderr)
            with Image.open(top) as image:
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)


if __name__ == "__main__":
    unittest.main()
