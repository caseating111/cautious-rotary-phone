from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_selection as custom
from tools import run_existing_pillow_from_config as pillow_adapter
from tools import standard_pillow_preview as preview


class StandardPillowPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.app.mkdir()
        self.image_root = self.root / "images"
        self.source_folder = self.image_root / "setA"
        self.source_folder.mkdir(parents=True)
        self.crops = self.root / "crops"
        self.crop_folder = self.crops / "setA"
        self.crop_folder.mkdir(parents=True)
        self.outputs = self.root / "outputs"
        self.grid = self.root / "grid.csv"
        self.images = self.root / "images.csv"
        self.conditions = self.root / "condition_order.csv"

        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\nE1,A,2,1,WT X\nE1,A,2,2,mut1\n",
            encoding="utf-8",
        )
        self.images.write_text(
            "Filename,Experiment,Set,Type\nplate1.jpg,E1,A,YPDA\n",
            encoding="utf-8",
        )
        self.conditions.write_text("Type,Order\nYPDA,1\n", encoding="utf-8")
        source = self.source_folder / "plate1.jpg"
        source.write_bytes(b"synthetic")
        source_mtime = source.stat().st_mtime_ns
        for column, strain in ((1, "WT X"), (2, "mut1")):
            for state in ("Top", "Low"):
                crop = self.crop_folder / f"E1_A_YPDA_{column:02d}_{state}_{strain}.png"
                Image.new("L", (130, 546), 40 + column).save(crop)
                os.utime(crop, ns=(source_mtime + 10_000_000, source_mtime + 10_000_000))

        self.config = {
            "image_root": str(self.image_root),
            "crop_output": str(self.crops),
            "matrix_output": str(self.outputs),
            "grid_csv": str(self.grid),
            "images_csv": str(self.images),
            "condition_order_csv": str(self.conditions),
            "crop_width": 130,
            "crop_height": 546,
        }
        self.config_file = self.app / "config.json"
        self.config_file.write_text(json.dumps(self.config), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def runtime_patches(self):
        return (
            patch.object(custom, "APP_DIR", self.app),
            patch.object(pillow_adapter, "APP_DIR", self.app),
            patch.object(pillow_adapter, "CONFIG_FILE", self.config_file),
            patch.object(pillow_adapter, "LAST_OUTPUT_FILE", self.app / "last_pillow_output.txt"),
        )

    def test_output_count_detects_multi_image_jobs(self) -> None:
        self.assertEqual(preview.estimated_output_count("matrices", self.config), 2)
        self.assertEqual(preview.estimated_output_count("all-strains", self.config), 2)
        self.assertEqual(preview.estimated_output_count("all-strains-dedup", self.config), 2)
        self.assertEqual(preview.estimated_output_count("label-individual", self.config, crop_count=4), 4)

    def test_all_strains_preview_builds_only_top_in_disposable_output(self) -> None:
        patches = self.runtime_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            result = preview.build_preview("all-strains")
            try:
                self.assertEqual(result.image.name, "ALL_Top_MATRIX.png")
                self.assertTrue(result.image.is_file())
                self.assertFalse(self.outputs.exists())
            finally:
                preview_root = result.image.parents[1]
                result.cleanup()
                self.assertFalse(preview_root.exists())

    def test_label_individual_preview_stages_one_crop_and_outputs_one_labelled_image(self) -> None:
        patches = self.runtime_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            result = preview.build_preview("label-individual")
            try:
                self.assertTrue(result.image.is_file())
                all_images = [
                    path for path in result.image.parents[2].rglob("*")
                    if path.is_file() and path.suffix.lower() in pillow_adapter.IMAGE_EXTENSIONS
                ]
                self.assertEqual(len(all_images), 2)  # one staged input + one labelled preview output
                self.assertFalse(self.outputs.exists())
            finally:
                result.cleanup()


if __name__ == "__main__":
    unittest.main()
