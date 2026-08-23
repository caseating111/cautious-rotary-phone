from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.preflight_batch import build_report


class GridInterpolationPreflightConstraintTests(unittest.TestCase):
    def make_project(
        self,
        root: Path,
        grid_cols: int,
        folder_name: str = "setA",
        with_current_crops: bool = False,
    ) -> dict:
        image_root = root / "images"
        source_folder = image_root / folder_name
        crop_root = root / "crops"
        output_folder = crop_root / folder_name
        source_folder.mkdir(parents=True)
        crop_root.mkdir()
        source = source_folder / "plate1.jpg"
        Image.new("L", (200, 200), 10).save(source)

        grid_csv = root / "grid.csv"
        images_csv = root / "images.csv"
        grid_rows = "".join(
            f"E1,A,{grid_cols},{column},{'WT' if column == 1 else f'mut{column}'}\n"
            for column in range(1, grid_cols + 1)
        )
        grid_csv.write_text(
            "Experiment,Set,GridCols,Column,Strain\n" + grid_rows,
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
            index = 0
            for column in range(1, grid_cols + 1):
                strain = "WT" if column == 1 else f"mut{column}"
                for state in ("Top", "Low"):
                    index += 1
                    path = output_folder / f"E1_A_YPDA_{column:02d}_{state}_{strain}.png"
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

    def test_one_column_grid_is_blocked_for_grid_interpolation_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_project(Path(temp), grid_cols=1)
            lines, problems, pending = build_report(config)

            self.assertTrue(problems)
            self.assertEqual([row["Filename"] for row in pending], ["plate1.jpg"])
            self.assertIn("GRIDS UNSUPPORTED BY GRID INTERPOLATION (1)", lines)
            self.assertIn("- E1/A: GridCols=1", lines)

    def test_same_one_column_project_is_valid_for_shared_non_fiji_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_project(Path(temp), grid_cols=1, with_current_crops=True)
            lines, problems, pending = build_report(
                config,
                require_grid_interpolation=False,
            )

            self.assertFalse(problems)
            self.assertEqual(pending, [])
            self.assertNotIn("GRIDS UNSUPPORTED BY GRID INTERPOLATION", lines)
            self.assertIn("Already complete images: 1", lines)

    def test_semicolon_source_folder_is_fiji_only_handoff_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_project(
                Path(temp),
                grid_cols=2,
                folder_name="set;A",
                with_current_crops=True,
            )

            fiji_lines, fiji_problems, _ = build_report(config)
            self.assertTrue(fiji_problems)
            self.assertIn("SOURCE FOLDERS UNSAFE FOR FIJI ARGUMENT HANDOFF (1)", fiji_lines)
            self.assertIn("- set;A", fiji_lines)

            shared_lines, shared_problems, pending = build_report(
                config,
                require_grid_interpolation=False,
                require_fiji_handoff_paths=False,
            )
            self.assertFalse(shared_problems)
            self.assertEqual(pending, [])
            self.assertNotIn("SOURCE FOLDERS UNSAFE FOR FIJI ARGUMENT HANDOFF", shared_lines)
            self.assertIn("Already complete images: 1", shared_lines)


if __name__ == "__main__":
    unittest.main()
