from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_selection as custom
from tools import run_custom_matrix_job as job
from tools import run_existing_pillow_from_config as pillow_adapter


class RecordedCustomMatrixJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_root = self.root / "images"
        self.source_folder = self.image_root / "setA"
        self.source_folder.mkdir(parents=True)
        self.crops = self.root / "crops"
        self.crops.mkdir()
        self.outputs = self.root / "outputs"
        self.grid = self.root / "grid.csv"
        self.images = self.root / "images.csv"
        self.conditions = self.root / "condition_order.csv"
        self.app = self.root / "app"
        self.app.mkdir()

        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E2,A,3,1,wt\n"
            "E2,A,3,2,mutA\n"
            "E2,A,3,3,mutB\n",
            encoding="utf-8",
        )
        self.images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E2,A,YPDA\n"
            "plate2.jpg,E2,A,SALT\n",
            encoding="utf-8",
        )
        self.conditions.write_text("Type,Order\nYPDA,1\nSALT,2\n", encoding="utf-8")
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
        self.selection = {
            "groups": [{"experiment": "E2", "set": "A", "columns": [1, 3]}],
            "conditions": ["SALT"],
            "states": ["Top"],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_source_and_crops(self, crop_mtime_offset_ns: int = 10_000_000) -> None:
        source = self.source_folder / "plate2.jpg"
        source.write_bytes(b"synthetic source")
        source_mtime = source.stat().st_mtime_ns
        for column, strain in ((1, "wt"), (3, "mutB")):
            for state in ("Top", "Low"):
                path = self.crops / f"E2_A_SALT_{column:02d}_{state}_{strain}.png"
                Image.new("L", (130, 546), 40 + column).save(path)
                os.utime(path, ns=(source_mtime + crop_mtime_offset_ns, source_mtime + crop_mtime_offset_ns))

    def patched_runtime(self):
        return (
            patch.object(custom, "APP_DIR", self.app),
            patch.object(custom, "LAST_SELECTION_FILE", self.app / "last_matrix_selection.json"),
            patch.object(pillow_adapter, "APP_DIR", self.app),
            patch.object(pillow_adapter, "CONFIG_FILE", self.config_file),
            patch.object(pillow_adapter, "LAST_OUTPUT_FILE", self.app / "last_pillow_output.txt"),
        )

    def test_job_builds_focused_output_and_separate_human_machine_records(self) -> None:
        self.write_source_and_crops()
        patches = self.patched_runtime()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            output = job.run_job(self.selection, no_open_output=True)

        self.assertEqual(sorted(path.name for path in output.glob("*.png")), ["E2_A_Top_MATRIX.png"])
        human = self.outputs / "Processing Logs" / f"{output.name}.txt"
        machine = self.outputs / "_workflow" / "output-recipes" / f"{output.name}.json"
        self.assertTrue(human.is_file())
        self.assertTrue(machine.is_file())
        self.assertIn("E2 / A: columns 1, 3", human.read_text(encoding="utf-8"))
        recipe = json.loads(machine.read_text(encoding="utf-8"))
        self.assertEqual(recipe["selection"], custom.normalize_selection(self.selection))
        self.assertEqual(recipe["crops"], {"required": 2, "available": 2, "used": 2})

    def test_job_rejects_selected_crop_older_than_source(self) -> None:
        self.write_source_and_crops(crop_mtime_offset_ns=10_000_000)
        source = self.source_folder / "plate2.jpg"
        future = max(source.stat().st_mtime_ns, *(path.stat().st_mtime_ns for path in self.crops.glob("*.png"))) + 20_000_000
        os.utime(source, ns=(future, future))

        patches = self.patched_runtime()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            with self.assertRaises(SystemExit) as caught:
                job.run_job(self.selection, no_open_output=True)

        self.assertIn("not current relative to their source images", str(caught.exception))
        self.assertFalse(self.outputs.exists())


if __name__ == "__main__":
    unittest.main()
