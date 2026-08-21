from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.preflight_batch import build_report


class PreflightWindowsCollisionTests(unittest.TestCase):
    def write_project(self, root: Path, second_experiment: str) -> dict:
        image_root = root / "images"
        source_folder = image_root / "setA"
        crop_root = root / "crops"
        source_folder.mkdir(parents=True)
        crop_root.mkdir()
        (source_folder / "plate1.jpg").write_bytes(b"source one")
        (source_folder / "plate2.jpg").write_bytes(b"source two")

        grid = root / "grid.csv"
        grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,2,1,WT\n"
            "E1,A,2,2,mut1\n"
            f"{second_experiment},A,2,1,WT\n"
            f"{second_experiment},A,2,2,mut1\n",
            encoding="utf-8",
        )
        images = root / "images.csv"
        images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            f"plate2.jpg,{second_experiment},A,YPDA\n",
            encoding="utf-8",
        )

        return {
            "image_root": str(image_root),
            "crop_output": str(crop_root),
            "grid_csv": str(grid),
            "images_csv": str(images),
            "crop_width": 20,
            "crop_height": 48,
        }

    def test_case_only_output_paths_are_blocked_for_windows_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.write_project(Path(temp), second_experiment="e1")

            lines, problems, _pending = build_report(config)
            text = "\n".join(lines).replace("\\", "/")

            self.assertTrue(problems)
            self.assertIn("OUTPUT PATH COLLISIONS (WINDOWS CASE-INSENSITIVE)", text)
            self.assertIn("E1_A_YPDA_01_Top_WT.png", text)
            self.assertIn("e1_A_YPDA_01_Top_WT.png", text)
            self.assertIn("setA/plate1.jpg", text)
            self.assertIn("setA/plate2.jpg", text)

    def test_genuinely_distinct_output_paths_remain_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.write_project(Path(temp), second_experiment="E2")

            lines, problems, pending = build_report(config)
            text = "\n".join(lines)

            self.assertFalse(problems, text)
            self.assertNotIn("OUTPUT PATH COLLISIONS (WINDOWS CASE-INSENSITIVE)", text)
            self.assertEqual(len(pending), 2)


if __name__ == "__main__":
    unittest.main()
