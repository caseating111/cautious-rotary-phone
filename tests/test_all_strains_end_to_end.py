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


class AllStrainsEndToEndTests(unittest.TestCase):
    def run_job(self, alias: str) -> tuple[subprocess.CompletedProcess[str], Path, list[Path]]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        home = root / "home"
        image_root = root / "images"
        source_folder = image_root / "setA"
        crop_root = root / "crops"
        crop_folder = crop_root / "setA"
        matrix_root = root / "matrices"
        app_dir = home / ".cautious-rotary-phone"
        source_folder.mkdir(parents=True)
        crop_folder.mkdir(parents=True)
        matrix_root.mkdir()
        app_dir.mkdir(parents=True)

        source = source_folder / "plate1.jpg"
        Image.new("L", (240, 200), 12).save(source)
        source_mtime = source.stat().st_mtime_ns

        grid_csv = root / "grid.csv"
        images_csv = root / "images.csv"
        conditions_csv = root / "condition_order.csv"
        grid_csv.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E2,A,3,1,WT Y\n"
            "E2,A,3,2,WT X\n"
            "E2,A,3,3,mut1\n",
            encoding="utf-8",
        )
        images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E2,A,YPDA\n",
            encoding="utf-8",
        )
        conditions_csv.write_text("Order,Type\n1,YPDA\n", encoding="utf-8")

        real_crops: list[Path] = []
        for index, (column, strain, state) in enumerate(
            (
                (1, "WT Y", "Top"),
                (1, "WT Y", "Low"),
                (2, "WT X", "Top"),
                (2, "WT X", "Low"),
                (3, "mut1", "Top"),
                (3, "mut1", "Low"),
            ),
            1,
        ):
            path = crop_folder / f"E2_A_YPDA_{column:02d}_{state}_{strain}.png"
            Image.new("L", (20, 48), 30 + column).save(path)
            os.utime(path, ns=(source_mtime + index, source_mtime + index))
            real_crops.append(path)

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
        env["USERPROFILE"] = str(home)
        result = subprocess.run(
            [sys.executable, str(WRAPPER), alias, "--no-open-output"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return result, matrix_root, real_crops

    def assert_real_crops_untouched(self, paths: list[Path]) -> None:
        for path in paths:
            with Image.open(path) as image:
                self.assertEqual(image.size, (20, 48))

    def test_all_strains_job_runs_through_staged_wrapper(self) -> None:
        result, matrix_root, real_crops = self.run_job("all-strains")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Crop orientation: rotated 6, already ready 0", result.stdout)
        self.assert_real_crops_untouched(real_crops)

        outputs = [path for path in matrix_root.iterdir() if path.is_dir()]
        self.assertEqual(len(outputs), 1)
        self.assertTrue(outputs[0].name.startswith("ALL STRAINS"))
        self.assertTrue((outputs[0] / "ALL_Top_MATRIX.png").is_file())
        self.assertTrue((outputs[0] / "ALL_Low_MATRIX.png").is_file())

    def test_all_strains_dedup_job_runs_through_staged_wrapper(self) -> None:
        result, matrix_root, real_crops = self.run_job("all-strains-dedup")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Crop orientation: rotated 6, already ready 0", result.stdout)
        self.assert_real_crops_untouched(real_crops)

        outputs = [path for path in matrix_root.iterdir() if path.is_dir()]
        self.assertEqual(len(outputs), 1)
        self.assertTrue(outputs[0].name.startswith("ALL STRAINS NO WT DUPE"))
        self.assertTrue((outputs[0] / "WT_EXP2A_ALL_Top.png").is_file())
        self.assertTrue((outputs[0] / "WT_EXP2A_ALL_Low.png").is_file())


if __name__ == "__main__":
    unittest.main()