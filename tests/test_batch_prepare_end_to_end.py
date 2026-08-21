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
BATCH_WRAPPER = REPO_ROOT / "tools" / "run_full_column_batch_from_config.py"


class BatchPrepareEndToEndTests(unittest.TestCase):
    def write_project(self, root: Path, grid_cols: int) -> tuple[Path, Path]:
        home = root / "home"
        app_dir = home / ".cautious-rotary-phone"
        image_root = root / "images"
        source_folder = image_root / "setA"
        crop_root = root / "crops"
        app_dir.mkdir(parents=True)
        source_folder.mkdir(parents=True)
        crop_root.mkdir()
        (source_folder / "plate1.jpg").write_bytes(b"synthetic source placeholder")

        grid_csv = root / "grid.csv"
        images_csv = root / "images.csv"
        conditions_csv = root / "condition_order.csv"
        grid_lines = ["Experiment,Set,GridCols,Column,Strain"]
        for column in range(1, grid_cols + 1):
            strain = "WT" if column == 1 else f"mut{column - 1}"
            grid_lines.append(f"E1,A,{grid_cols},{column},{strain}")
        grid_csv.write_text("\n".join(grid_lines) + "\n", encoding="utf-8")
        images_csv.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )
        conditions_csv.write_text("Order,Type\n1,YPDA\n", encoding="utf-8")

        # Deliberately omit fiji_executable: prepare-only must not require it.
        (app_dir / "config.json").write_text(
            json.dumps(
                {
                    "image_root": str(image_root),
                    "crop_output": str(crop_root),
                    "grid_csv": str(grid_csv),
                    "images_csv": str(images_csv),
                    "condition_order_csv": str(conditions_csv),
                    "crop_width": 20,
                    "crop_height": 48,
                    "alignment_tolerance": 0.05,
                }
            ),
            encoding="utf-8",
        )
        return home, app_dir

    def run_prepare(self, home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(BATCH_WRAPPER), "--prepare-only", *extra],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_prepare_only_builds_real_composed_macro_without_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, app_dir = self.write_project(Path(temp), grid_cols=2)
            result = self.run_prepare(home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Prepared composed batch for 1 pending image(s)", result.stdout)

            pending = app_dir / "pending_images.csv"
            self.assertTrue(pending.is_file())
            with pending.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["Filename"] for row in rows], ["plate1.jpg"])

            configured = app_dir / "batch_full_column.configured.ijm"
            self.assertTrue(configured.is_file())
            text = configured.read_text(encoding="utf-8")
            self.assertIn("FULL-COLUMN COMPOSED ROUTE", text)
            self.assertIn('"context=" + experiment + "/" + setName + "/" + typeName', text)
            self.assertIn("CROP_W = 20;", text)
            self.assertIn("CROP_H = 48;", text)
            self.assertNotIn("1 / 4 — R1C1", text)
            self.assertNotIn("4 / 4 — R5C", text)

    def test_prepare_only_builds_preserved_four_point_fallback_without_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, app_dir = self.write_project(Path(temp), grid_cols=10)
            result = self.run_prepare(home, "--legacy")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Prepared four-point fallback batch for 1 pending image(s)", result.stdout)

            pending = app_dir / "pending_images.csv"
            self.assertTrue(pending.is_file())
            with pending.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["Filename"] for row in rows], ["plate1.jpg"])

            configured = app_dir / "batch_four_point_fallback.configured.ijm"
            self.assertTrue(configured.is_file())
            text = configured.read_text(encoding="utf-8")
            self.assertIn("1 / 4 — R1C1", text)
            self.assertIn("4 / 4 — R5C", text)
            self.assertIn("CROP_W = 20;", text)
            self.assertIn("CROP_H = 48;", text)
            self.assertNotIn("FULL-COLUMN COMPOSED ROUTE", text)
            self.assertNotIn('"path here"', text)


if __name__ == "__main__":
    unittest.main()
