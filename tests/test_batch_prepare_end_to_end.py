from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_WRAPPER = REPO_ROOT / "tools" / "run_four_point_batch_from_config.py"


class BatchPrepareEndToEndTests(unittest.TestCase):
    def write_project(self, root: Path) -> tuple[Path, Path, Path]:
        home = root / "home"
        app_dir = home / ".cautious-rotary-phone"
        source_folder = root / "images" / "setA"
        crop_root = root / "derived" / "crops"
        matrix_root = root / "derived" / "matrices"
        app_dir.mkdir(parents=True)
        source_folder.mkdir(parents=True)
        (source_folder / "plate1.jpg").write_bytes(b"synthetic source placeholder")

        grid = root / "grid.csv"
        grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            + "".join(f"E1,A,10,{column},S{column}\n" for column in range(1, 11)),
            encoding="utf-8",
        )
        images = root / "images.csv"
        images.write_text("Filename,Experiment,Set,Type\nplate1.jpg,E1,A,YPDA\n", encoding="utf-8")
        conditions = root / "condition_order.csv"
        conditions.write_text("Order,Type\n1,YPDA\n", encoding="utf-8")
        (app_dir / "config.json").write_text(
            json.dumps(
                {
                    "image_root": str(root / "images"),
                    "crop_output": str(crop_root),
                    "matrix_output": str(matrix_root),
                    "grid_csv": str(grid),
                    "images_csv": str(images),
                    "condition_order_csv": str(conditions),
                    "crop_width": 20,
                    "crop_height": 48,
                }
            ),
            encoding="utf-8",
        )
        return home, app_dir, crop_root

    def test_prepare_only_builds_current_four_point_macro_without_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, app_dir, crop_root = self.write_project(Path(temp))
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["USERPROFILE"] = str(home)
            result = subprocess.run(
                [sys.executable, str(BATCH_WRAPPER), "--prepare-only"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Prepared four-point batch for 1 pending image(s)", result.stdout)
            self.assertTrue(crop_root.is_dir())

            pending = app_dir / "pending_images.tsv"
            with pending.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual([row["Filename"] for row in rows], ["plate1.jpg"])
            self.assertEqual(rows[0]["Folder"], "setA")

            configured = app_dir / "four_point_batch.configured.ijm"
            text = configured.read_text(encoding="utf-8")
            self.assertIn("FOUR-POINT MATHEMATICAL ALIGNMENT + QC", text)
            self.assertIn("1 / 4 -- R1C1", text)
            self.assertIn("4 / 4 -- R5C", text)
            self.assertEqual(text.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
            self.assertIn("claheBlock = maxOf(400, round(roiBoxSize * 4));", text)
            self.assertIn("CROP_W = 20;", text)
            self.assertIn("CROP_H = 48;", text)
            self.assertIn("requireCropFits(", text)
            self.assertIn(r'File.saveString("complete\n", controlFile);', text)
            self.assertIn('runLabel = "Batch All";', text)
            self.assertIn('runSequence = "001";', text)
            self.assertIn("function workflowLog(message)", text)
            self.assertIn("function completeWorkflowRun(processed, notListed, skipped)", text)
            self.assertNotIn("print(", text)
            self.assertIn("Processing Logs/Four-Point Alignment Runs.txt", text)
            self.assertNotIn("FULL-COLUMN COMPOSED ROUTE", text)


if __name__ == "__main__":
    unittest.main()
