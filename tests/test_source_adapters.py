from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import run_existing_pillow_from_config as pillow_adapter
from tools import run_full_column_batch_from_config as batch_adapter


class SourceAdapterTests(unittest.TestCase):
    def test_full_column_batch_keeps_loop_and_replaces_calibration(self) -> None:
        config = {
            "grid_csv": "C:/project/grid.csv",
            "images_csv": "C:/project/images.csv",
            "image_root": "C:/project/images",
            "crop_output": "C:/project/crops",
            "alignment_tolerance": 0.05,
            "crop_width": 140,
            "crop_height": 560,
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "batch.ijm"
            pending = Path(temp) / "pending_images.csv"
            with patch.object(batch_adapter, "CONFIGURED_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ):
                built = batch_adapter.build_macro(config)

            text = built.read_text(encoding="utf-8")
            self.assertIn('gridFile   = "C:/project/grid.csv";', text)
            self.assertIn(str(pending).replace("\\", "/"), text)
            self.assertIn('inputRoot  = "C:/project/images";', text)
            self.assertIn('outputRoot = "C:/project/crops";', text)
            self.assertIn("CROP_W = 140;", text)
            self.assertIn("CROP_H = 560;", text)
            self.assertIn("tolerance=0.05", text)
            self.assertIn("folders = getFileList(inputRoot);", text)
            self.assertIn("runMacro(", text)
            self.assertNotIn("1 / 4 — R1C1", text)
            self.assertNotIn("4 / 4 — R5C", text)

    def test_all_pillow_aliases_only_replace_shared_path_block(self) -> None:
        config = {
            "crop_output": "C:/project/crops",
            "matrix_output": "C:/project/matrices",
            "grid_csv": "C:/project/grid.csv",
            "images_csv": "C:/project/images.csv",
            "condition_order_csv": "C:/project/condition_order.csv",
        }
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(pillow_adapter, "APP_DIR", Path(temp)):
                for alias in pillow_adapter.SCRIPTS:
                    with self.subTest(alias=alias):
                        configured = pillow_adapter.configured_copy(alias, config)
                        text = configured.read_text(encoding="utf-8")
                        self.assertIn("IMAGE_ROOT = Path('C:/project/crops')", text)
                        self.assertIn("GRID_CSV = Path('C:/project/grid.csv')", text)
                        self.assertIn("IMAGES_CSV = Path('C:/project/images.csv')", text)
                        self.assertIn("CONDITION_ORDER_CSV = Path('C:/project/condition_order.csv')", text)
                        self.assertIn("MATRIX_ROOT = Path('C:/project/matrices')", text)
                        self.assertIn("ROTATE_IMAGES_90_CCW = False", text)
                        self.assertNotIn('Path(r"path here")', text)

    def test_crop_orientation_normalization_only_rotates_portrait_crops_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "setA"
            folder.mkdir()
            portrait = folder / "portrait.png"
            landscape = folder / "landscape.png"
            unexpected = folder / "unexpected.png"
            Image.new("L", (130, 546), 10).save(portrait)
            Image.new("L", (546, 130), 20).save(landscape)
            Image.new("L", (100, 100), 30).save(unexpected)

            first = pillow_adapter.normalize_crop_orientation(root, 130, 546)
            self.assertEqual(first, (1, 1, 1))
            with Image.open(portrait) as image:
                self.assertEqual(image.size, (546, 130))

            second = pillow_adapter.normalize_crop_orientation(root, 130, 546)
            self.assertEqual(second, (0, 2, 1))


if __name__ == "__main__":
    unittest.main()
