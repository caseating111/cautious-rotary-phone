from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_one_plate_validation as proof


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_WRAPPER = REPO_ROOT / "tools" / "run_full_column_batch_from_config.py"


class BatchPrepareEndToEndTests(unittest.TestCase):
    def write_project(self, root: Path, grid_cols: int) -> tuple[Path, Path, Path]:
        home = root / "home"
        app_dir = home / ".cautious-rotary-phone"
        image_root = root / "images"
        source_folder = image_root / "setA"
        crop_root = root / "derived" / "crops"
        app_dir.mkdir(parents=True)
        source_folder.mkdir(parents=True)
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
        return home, app_dir, crop_root

    def run_prepare(self, home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        return subprocess.run(
            [sys.executable, str(BATCH_WRAPPER), "--prepare-only", *extra],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_prepare_only_builds_real_composed_macro_without_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, app_dir, crop_root = self.write_project(Path(temp), grid_cols=2)
            self.assertFalse(crop_root.exists())
            result = self.run_prepare(home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Prepared composed batch for 1 pending image(s)", result.stdout)
            self.assertTrue(crop_root.is_dir())

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

    def test_prepare_only_builds_four_point_math_qc_without_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, app_dir, crop_root = self.write_project(Path(temp), grid_cols=10)
            self.assertFalse(crop_root.exists())
            result = self.run_prepare(home, "--legacy")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Prepared four-point batch for 1 pending image(s)", result.stdout)
            self.assertTrue(crop_root.is_dir())

            pending = app_dir / "pending_images.csv"
            self.assertTrue(pending.is_file())
            with pending.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["Filename"] for row in rows], ["plate1.jpg"])

            configured = app_dir / "batch_four_point_fallback.configured.ijm"
            self.assertTrue(configured.is_file())
            text = configured.read_text(encoding="utf-8")
            self.assertIn("FOUR-POINT MATHEMATICAL ALIGNMENT + QC", text)
            self.assertIn("1 / 4 — R1C1", text)
            self.assertIn("4 / 4 — R5C", text)
            self.assertIn('Dialog.create("Full-grid QC")', text)
            self.assertEqual(text.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
            self.assertIn("claheBlock = round(roiBoxSize * 3.3)", text)
            self.assertIn('histogram=256 maximum=1000 mask=*None* fast_(less_accurate)', text)
            self.assertNotIn("CLICK_ROI = 108", text)
            self.assertIn('roiBoxW = parseFloat(call("ij.Prefs.get", "rect.width", 108))', text)
            self.assertNotIn('run("Show All")', text)
            self.assertIn('startsWith(IJ.getToolName, "Rotated Rectangle Click Tool")', text)
            self.assertNotIn("makeRectangle(round(viewW / 2", text)
            self.assertIn("Overlay.drawLine(p1x, p1y, p2x, p2y)", text)
            self.assertIn("CROP_W = 20;", text)
            self.assertIn("CROP_H = 48;", text)
            self.assertNotIn("FULL-COLUMN COMPOSED ROUTE", text)
            self.assertNotIn('"path here"', text)
            self.assertIn("lowerFileName = toLowerCase(fileName)", text)
            self.assertIn("startsWith(lowerLine, plainPrefix)", text)

            proof_csv = app_dir / "one_plate_validation_images.csv"
            proof_macro = app_dir / "one_plate_four_point_validation.configured.ijm"
            completed = type("Completed", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
            with patch.object(proof.batch, "PENDING_IMAGES_CSV", pending), patch.object(
                proof.batch, "CONFIGURED_LEGACY_MACRO", configured
            ), patch.object(proof, "PROOF_IMAGES_CSV", proof_csv), patch.object(
                proof, "PROOF_LEGACY_MACRO", proof_macro
            ), patch.object(proof.subprocess, "run", return_value=completed):
                built, selected = proof.prepare("plate1.jpg", legacy=True)

            self.assertEqual(built, proof_macro)
            self.assertEqual(selected["Filename"], "plate1.jpg")
            proof_text = proof_macro.read_text(encoding="utf-8")
            self.assertEqual(proof_text.count('run("Enhance Local Contrast (CLAHE)", claheOptions)'), 2)
            self.assertIn(proof.batch.macro_path(proof_csv), proof_text)

            ahk_text = (REPO_ROOT / "ahk" / "full_column_alignment_hotkeys.ah2").read_text(encoding="utf-8")
            self.assertIn("#Requires AutoHotkey v2.0", ahk_text)
            for title in ("1 / 4", "2 / 4", "3 / 4", "4 / 4", "Full-grid QC"):
                self.assertIn(f'"{title}"', ahk_text)


if __name__ == "__main__":
    unittest.main()
