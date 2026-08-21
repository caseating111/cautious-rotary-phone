from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "tools" / "run_existing_pillow_from_config.py"


class PillowWrapperEndToEndTests(unittest.TestCase):
    def test_complete_synthetic_project_builds_matrices_through_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            crop_root = root / "crops"
            crop_folder = crop_root / "setA"
            matrix_root = root / "matrices"
            app_dir = home / ".cautious-rotary-phone"
            crop_folder.mkdir(parents=True)
            matrix_root.mkdir()
            app_dir.mkdir(parents=True)

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

            # Configured unrotated size is 20x48; provide already-ready 48x20 crops.
            for column, strain in ((1, "WT"), (2, "mut1")):
                for state in ("Top", "Low"):
                    path = crop_folder / f"E1_A_YPDA_{column:02d}_{state}_{strain}.png"
                    Image.new("L", (48, 20), 30 + column).save(path)

            (app_dir / "config.json").write_text(
                json.dumps(
                    {
                        "crop_output": str(crop_root),
                        "matrix_output": str(matrix_root),
                        "grid_csv": str(grid_csv),
                        "images_csv": str(images_csv),
                        "condition_order_csv": str(conditions_csv),
                        "crop_width": 20,
                        "crop_height": 48,
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["HOME"] = str(home)
            result = subprocess.run(
                [sys.executable, str(WRAPPER), "matrices", "--no-open-output"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Crop orientation: rotated 0, already ready 4", result.stdout)

            outputs = sorted(path for path in matrix_root.iterdir() if path.is_dir())
            self.assertEqual(len(outputs), 1)
            self.assertTrue((outputs[0] / "E1_A_Top_MATRIX.png").is_file())
            self.assertTrue((outputs[0] / "E1_A_Low_MATRIX.png").is_file())


if __name__ == "__main__":
    unittest.main()
