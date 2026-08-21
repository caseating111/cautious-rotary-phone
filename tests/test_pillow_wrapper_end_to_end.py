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
    def test_complete_synthetic_project_stages_exact_crops_without_mutating_real_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            image_root = root / "images"
            source_folder = image_root / "setA"
            crop_root = root / "crops"
            crop_folder = crop_root / "setA"
            stale_folder = crop_root / "old"
            matrix_root = root / "matrices"
            app_dir = home / ".cautious-rotary-phone"
            source_folder.mkdir(parents=True)
            crop_folder.mkdir(parents=True)
            stale_folder.mkdir(parents=True)
            matrix_root.mkdir()
            app_dir.mkdir(parents=True)

            source = source_folder / "plate1.jpg"
            Image.new("L", (200, 200), 12).save(source)
            source_mtime = source.stat().st_mtime_ns

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

            # Configured unrotated size is 20x48. Keep the real crops unrotated;
            # the wrapper should rotate only disposable staged copies.
            real_crops: list[Path] = []
            for index, (column, strain, state) in enumerate(
                (
                    (1, "WT", "Top"),
                    (1, "WT", "Low"),
                    (2, "mut1", "Top"),
                    (2, "mut1", "Low"),
                ),
                1,
            ):
                path = crop_folder / f"E1_A_YPDA_{column:02d}_{state}_{strain}.png"
                Image.new("L", (20, 48), 30 + column).save(path)
                os.utime(path, ns=(source_mtime + index, source_mtime + index))
                real_crops.append(path)

            # This old prefix-compatible file would confuse the untouched legacy
            # startswith() lookup if the wrapper pointed it at crop_root directly.
            stale = stale_folder / "E1_A_YPDA_01_Top_OLD.png"
            Image.new("L", (48, 20), 99).save(stale)

            (app_dir / "config.json").write_text(
                json.dumps(
                    {
                        "image_root": str(image_root),
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
            self.assertIn("Ignoring 1 stale prefix-compatible crop file(s)", result.stdout)
            self.assertIn("Crop orientation: rotated 4, already ready 0", result.stdout)

            for path in real_crops:
                with Image.open(path) as image:
                    self.assertEqual(image.size, (20, 48))

            outputs = sorted(path for path in matrix_root.iterdir() if path.is_dir())
            self.assertEqual(len(outputs), 1)
            self.assertTrue((outputs[0] / "E1_A_Top_MATRIX.png").is_file())
            self.assertTrue((outputs[0] / "E1_A_Low_MATRIX.png").is_file())


if __name__ == "__main__":
    unittest.main()
