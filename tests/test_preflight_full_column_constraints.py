from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.preflight_batch import build_report


class FullColumnPreflightConstraintTests(unittest.TestCase):
    def make_one_column_project(self, root: Path, with_current_crops: bool = False) -> dict:
        image_root = root / "images"
        source_folder = image_root / "setA"
        crop_root = root / "crops"
        output_folder = crop_root / "setA"
        source_folder.mkdir(parents=True)
        crop_root.mkdir()
        source = source_folder / "plate1.jpg"
        Image.new("L", (200, 200), 10).save(source)

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

        if with_current_crops:
            output_folder.mkdir()
            source_mtime = source.stat().st_mtime_ns
            for index, state in enumerate(("Top", "Low"), 1):
                path = output_folder / f"E1_A_YPDA_01_{state}_WT.png"
                Image.new("L", (130, 546), 20).save(path)
                os.utime(path, ns=(source_mtime + index, source_mtime + index))

        return {
            "image_root": str(image_root),
            "crop_output": str(crop_root),
            "grid_csv": str(grid_csv),
            "images_csv": str(images_csv),
            "crop_width": 130,
            "crop_height": 546,
        }

    def test_one_column_grid_is_blocked_for_full_column_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_one_column_project(Path(temp))
            lines, problems, pending = build_report(config)

            self.assertTrue(problems)
            self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
            self.assertIn("GRIDS UNSUPPORTED BY FULL-COLUMN ALIGNMENT (1)", lines)
            self.assertIn("- E1/A: GridCols=1", lines)

    def test_same_one_column_project_is_valid_for_shared_non_fiji_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_one_column_project(Path(temp), with_current_crops=True)
            lines, problems, pending = build_report(
                config,
                require_full_column_geometry=False,
            )

            self.assertFalse(problems)
            self.assertEqual(pending, [])
            self.assertNotIn("GRIDS UNSUPPORTED BY FULL-COLUMN ALIGNMENT", lines)
            self.assertIn("Already complete images: 1", lines)


if __name__ == "__main__":
    unittest.main()
