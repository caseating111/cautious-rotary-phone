from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_preview as preview
from tools import custom_matrix_selection as custom
from tools import run_existing_pillow_from_config as pillow_adapter


class CustomMatrixPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_root = self.root / "images"
        self.source_folder = self.image_root / "setA"
        self.source_folder.mkdir(parents=True)
        self.crop_root = self.root / "crops"
        self.crop_root.mkdir()
        self.output_root = self.root / "outputs"
        self.grid = self.root / "grid.csv"
        self.images = self.root / "images.csv"
        self.conditions = self.root / "condition_order.csv"
        self.app = self.root / "app"
        self.app.mkdir()

        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,2,1,WT\n"
            "E1,A,2,2,mut1\n"
            "E2,B,2,1,WT\n"
            "E2,B,2,2,mut2\n",
            encoding="utf-8",
        )
        self.images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,A,YPDA\n"
            "plate2.jpg,E2,B,YPDA\n",
            encoding="utf-8",
        )
        self.conditions.write_text("Type,Order\nYPDA,1\n", encoding="utf-8")
        self.config = {
            "image_root": str(self.image_root),
            "crop_output": str(self.crop_root),
            "matrix_output": str(self.output_root),
            "grid_csv": str(self.grid),
            "images_csv": str(self.images),
            "condition_order_csv": str(self.conditions),
            "crop_width": 130,
            "crop_height": 546,
        }
        self.config_file = self.app / "config.json"
        self.config_file.write_text(json.dumps(self.config), encoding="utf-8")
        self.selection = {
            "groups": [
                {"experiment": "E1", "set": "A", "columns": [1, 2]},
                {"experiment": "E2", "set": "B", "columns": [1, 2]},
            ],
            "conditions": ["YPDA"],
            "states": ["Top", "Low"],
        }

        for filename, exp, set_name, strains in (
            ("plate1.jpg", "E1", "A", ((1, "WT"), (2, "mut1"))),
            ("plate2.jpg", "E2", "B", ((1, "WT"), (2, "mut2"))),
        ):
            source = self.source_folder / filename
            source.write_bytes(b"synthetic")
            source_mtime = source.stat().st_mtime_ns
            for column, strain in strains:
                for state in ("Top", "Low"):
                    crop = self.crop_root / f"{exp}_{set_name}_YPDA_{column:02d}_{state}_{strain}.png"
                    Image.new("L", (130, 546), column * 30).save(crop)
                    os.utime(crop, ns=(source_mtime + 10_000_000, source_mtime + 10_000_000))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_output_count_matches_group_times_state_count(self) -> None:
        self.assertEqual(preview.output_count(self.selection), 4)
        representative = preview.representative_selection(self.selection)
        self.assertEqual(representative["groups"], [self.selection["groups"][0]])
        self.assertEqual(representative["states"], ["Top"])

    def test_preview_builds_exactly_one_disposable_matrix(self) -> None:
        with patch.object(custom, "APP_DIR", self.app), patch.object(
            pillow_adapter, "APP_DIR", self.app
        ), patch.object(pillow_adapter, "CONFIG_FILE", self.config_file), patch.object(
            pillow_adapter, "LAST_OUTPUT_FILE", self.app / "last_pillow_output.txt"
        ):
            result = preview.build_preview(self.selection)
            try:
                self.assertTrue(result.image.is_file())
                self.assertEqual(result.image.name, "E1_A_Top_MATRIX.png")
                self.assertFalse(self.output_root.exists())
            finally:
                preview_root = result.image.parents[1]
                result.cleanup()
                self.assertFalse(preview_root.exists())


if __name__ == "__main__":
    unittest.main()
