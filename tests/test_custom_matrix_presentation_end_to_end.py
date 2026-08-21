from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_selection as custom
from tools import run_custom_matrix_presentation as presentation_job
from tools import run_existing_pillow_from_config as pillow_adapter


class CustomMatrixPresentationEndToEndTests(unittest.TestCase):
    def test_presentation_job_uses_archived_range_without_touching_real_crop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "app"
            app.mkdir()
            range_dir = app / "display-ranges"
            range_dir.mkdir()
            image_root = root / "images"
            source_folder = image_root / "setA"
            source_folder.mkdir(parents=True)
            crop_root = root / "crops"
            crop_root.mkdir()
            output_root = root / "outputs"
            grid = root / "grid.csv"
            images = root / "images.csv"
            conditions = root / "condition_order.csv"

            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\nE2,A,1,1,WT\n",
                encoding="utf-8",
            )
            images.write_text(
                "Filename,Experiment,Set,Type\nplate1.jpg,E2,A,YPDA\n",
                encoding="utf-8",
            )
            conditions.write_text("Type,Order\nYPDA,1\n", encoding="utf-8")
            source = source_folder / "plate1.jpg"
            source.write_bytes(b"synthetic")
            source_mtime = source.stat().st_mtime_ns

            real_crop = crop_root / "E2_A_YPDA_01_Top_WT.png"
            low_crop = crop_root / "E2_A_YPDA_01_Low_WT.png"
            for path in (real_crop, low_crop):
                image = Image.new("L", (130, 546), 60)
                image.save(path)
                os.utime(path, ns=(source_mtime + 10_000_000, source_mtime + 10_000_000))
            original_bytes = real_crop.read_bytes()

            range_dir.joinpath("plate1.jpg.txt").write_text(
                "source_filename=plate1.jpg\nblack_point=10\nhigh_point=110\n",
                encoding="utf-8",
            )
            config = {
                "image_root": str(image_root),
                "crop_output": str(crop_root),
                "matrix_output": str(output_root),
                "grid_csv": str(grid),
                "images_csv": str(images),
                "condition_order_csv": str(conditions),
                "crop_width": 130,
                "crop_height": 546,
            }
            config_file = app / "config.json"
            config_file.write_text(json.dumps(config), encoding="utf-8")
            selection = {
                "groups": [{"experiment": "E2", "set": "A", "columns": [1]}],
                "conditions": ["YPDA"],
                "states": ["Top"],
            }

            with patch.object(custom, "APP_DIR", app), patch.object(
                pillow_adapter, "APP_DIR", app
            ), patch.object(pillow_adapter, "CONFIG_FILE", config_file), patch.object(
                pillow_adapter, "LAST_OUTPUT_FILE", app / "last_pillow_output.txt"
            ):
                output = presentation_job.run_job(selection, no_open_output=True)

            self.assertTrue((output / "E2_A_Top_MATRIX.png").is_file())
            self.assertEqual(real_crop.read_bytes(), original_bytes)
            recipe = json.loads(
                (output_root / "_workflow" / "output-recipes" / f"{output.name}.json").read_text(encoding="utf-8")
            )
            self.assertIn("presentation normalized", recipe["display_mode"])


if __name__ == "__main__":
    unittest.main()
