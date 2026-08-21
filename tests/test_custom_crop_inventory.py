from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_crop_inventory as inventory
from tools import custom_matrix_selection as custom


class CustomCropInventoryTests(unittest.TestCase):
    def test_inventory_distinguishes_current_missing_and_stale_selected_cells(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "app"
            app.mkdir()
            image_root = root / "images"
            source_folder = image_root / "setA"
            source_folder.mkdir(parents=True)
            crops = root / "crops"
            crops.mkdir()
            grid = root / "grid.csv"
            images = root / "images.csv"
            conditions = root / "condition_order.csv"

            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E2,A,3,1,WT\n"
                "E2,A,3,2,mutA\n"
                "E2,A,3,3,mutB\n",
                encoding="utf-8",
            )
            images.write_text(
                "Filename,Experiment,Set,Type\nplate1.jpg,E2,A,YPDA\n",
                encoding="utf-8",
            )
            conditions.write_text("Type,Order\nYPDA,1\n", encoding="utf-8")
            source = source_folder / "plate1.jpg"
            source.write_bytes(b"source")
            source_mtime = source.stat().st_mtime_ns

            current = crops / "E2_A_YPDA_01_Top_WT.png"
            stale = crops / "E2_A_YPDA_03_Top_mutB.png"
            Image.new("L", (130, 546), 10).save(current)
            Image.new("L", (130, 546), 20).save(stale)
            os.utime(current, ns=(source_mtime + 10_000_000, source_mtime + 10_000_000))
            os.utime(stale, ns=(max(0, source_mtime - 10_000_000), max(0, source_mtime - 10_000_000)))

            config = {
                "image_root": str(image_root),
                "crop_output": str(crops),
                "matrix_output": str(root / "outputs"),
                "grid_csv": str(grid),
                "images_csv": str(images),
                "condition_order_csv": str(conditions),
                "crop_width": 130,
                "crop_height": 546,
            }
            selection = {
                "groups": [{"experiment": "E2", "set": "A", "columns": [1, 2, 3]}],
                "conditions": ["YPDA"],
                "states": ["Top"],
            }

            with patch.object(custom, "APP_DIR", app):
                items = inventory.selected_inventory(config, selection)

            self.assertEqual([item.status for item in items], ["current", "missing", "stale"])
            self.assertEqual(inventory.source_plates_to_rerun(items), ["plate1.jpg"])
            summary = inventory.inventory_summary(items)
            self.assertIn("Current: 1", summary)
            self.assertIn("Missing: 1", summary)
            self.assertIn("Stale: 1", summary)
            self.assertIn("Source plates to rerun (1):", summary)
            self.assertIn("- plate1.jpg", summary)
            self.assertIn("col 2 mutA", summary)
            self.assertIn("col 3 mutB", summary)

    def test_missing_crop_with_missing_source_is_not_presented_as_rerunnable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "app"
            app.mkdir()
            image_root = root / "images"
            (image_root / "setA").mkdir(parents=True)
            crops = root / "crops"
            crops.mkdir()
            grid = root / "grid.csv"
            images = root / "images.csv"
            conditions = root / "condition_order.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\nE2,A,1,1,WT\n",
                encoding="utf-8",
            )
            images.write_text(
                "Filename,Experiment,Set,Type\nmissing_plate.jpg,E2,A,YPDA\n",
                encoding="utf-8",
            )
            conditions.write_text("Type,Order\nYPDA,1\n", encoding="utf-8")
            config = {
                "image_root": str(image_root),
                "crop_output": str(crops),
                "matrix_output": str(root / "outputs"),
                "grid_csv": str(grid),
                "images_csv": str(images),
                "condition_order_csv": str(conditions),
                "crop_width": 130,
                "crop_height": 546,
            }
            selection = {
                "groups": [{"experiment": "E2", "set": "A", "columns": [1]}],
                "conditions": ["YPDA"],
                "states": ["Top"],
            }

            with patch.object(custom, "APP_DIR", app):
                items = inventory.selected_inventory(config, selection)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].status, "source missing")
            self.assertEqual(inventory.source_plates_to_rerun(items), [])
            self.assertNotIn("Source plates to rerun", inventory.inventory_summary(items))


if __name__ == "__main__":
    unittest.main()