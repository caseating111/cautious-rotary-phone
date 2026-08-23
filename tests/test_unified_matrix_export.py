from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_selection as custom
from tools import run_existing_pillow_from_config as pillow_adapter
from tools import unified_matrix_export as unified


class UnifiedMatrixExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.app.mkdir()
        self.image_root = self.root / "images"
        (self.image_root / "E1").mkdir(parents=True)
        (self.image_root / "E2").mkdir()
        self.crops = self.root / "crops"
        self.crops.mkdir()
        self.matrices = self.root / "Matrices"
        self.metadata = self.root / "Metadata"
        self.metadata.mkdir()
        self.grid = self.metadata / "grid.csv"
        self.images = self.metadata / "images.csv"
        self.conditions = self.metadata / "condition_order.csv"
        self.config_file = self.app / "config.json"

        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,0,3,1,WT-A\n"
            "E1,0,3,2,WT-C\n"
            "E1,0,3,3,mut_one\n"
            "E2,A,3,1,WT_A\n"
            "E2,A,3,2,WT-B\n"
            "E2,A,3,3,mut_two\n",
            encoding="utf-8",
        )
        self.images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.png,E1,0,COND_1\n"
            "plate2.png,E2,A,COND_1\n",
            encoding="utf-8",
        )
        self.conditions.write_text("Type,Order\nCOND_1,1\nUNRUN,2\n", encoding="utf-8")
        source_times = {}
        for folder, filename in (("E1", "plate1.png"), ("E2", "plate2.png")):
            source = self.image_root / folder / filename
            Image.new("L", (80, 80), 5).save(source)
            source_times[folder] = source.stat().st_mtime_ns

        for exp, set_name, strain, column in (
            ("E1", "0", "WT-A", 1),
            ("E1", "0", "WT-C", 2),
            ("E1", "0", "mut_one", 3),
            ("E2", "A", "WT_A", 1),
            ("E2", "A", "WT-B", 2),
            ("E2", "A", "mut_two", 3),
        ):
            for state in ("Top", "Low"):
                crop = self.crops / f"{exp}_{set_name}_COND_1_{column:02d}_{state}_{strain}.png"
                Image.new("L", (20, 48), 20 + column).save(crop)
                stamp = source_times[exp] + 10_000_000
                os.utime(crop, ns=(stamp, stamp))

        self.config = {
            "image_root": str(self.image_root),
            "crop_output": str(self.crops),
            "matrix_output": str(self.matrices),
            "grid_csv": str(self.grid),
            "images_csv": str(self.images),
            "condition_order_csv": str(self.conditions),
            "crop_width": 20,
            "crop_height": 48,
        }
        self.config_file.write_text(json.dumps(self.config), encoding="utf-8")
        self.request = {
            "selection": {
                "groups": [
                    {"experiment": "E1", "set": "0", "columns": [1, 2, 3]},
                    {"experiment": "E2", "set": "A", "columns": [1, 2, 3]},
                ],
                "conditions": ["COND_1"],
                "states": ["Top", "Low"],
            },
            "outputs": list(unified.OUTPUT_TYPES),
            "preferred_wt": {"experiment": "e2", "set": "a"},
            "normalize_wt_names": True,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def runtime(self):
        return (
            patch.object(custom, "APP_DIR", self.app),
            patch.object(custom, "LAST_SELECTION_FILE", self.app / "last_matrix_selection.json"),
            patch.object(pillow_adapter, "APP_DIR", self.app),
            patch.object(pillow_adapter, "CONFIG_FILE", self.config_file),
            patch.object(pillow_adapter, "LAST_OUTPUT_FILE", self.app / "last_pillow_output.txt"),
        )

    def run_export(self) -> dict:
        patches = self.runtime()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            return unified.run_job(self.request, no_open_output=True)

    def test_all_outputs_publish_in_one_numbered_run_and_preserve_sources(self) -> None:
        original_sizes = {}
        for path in self.crops.glob("*.png"):
            with Image.open(path) as image:
                original_sizes[path.name] = image.size
        first = self.run_export()
        self.assertEqual(first["run_id"], "Run001")
        self.assertEqual(len(first["published_paths"]), 28)
        date = datetime.now().strftime("%d.%m.%y")

        aggregate = self.matrices / "!All Matrix Exports"
        aggregate_names = {path.name for path in aggregate.glob("*.png")}
        self.assertEqual(len(aggregate_names), 8)
        self.assertTrue(any(f"Run001_{date}_ALLmatrix_Top.png" == name for name in aggregate_names))
        self.assertTrue(
            any(
                f"Run001_{date}_E1.0-WTC_E2.A-WTAWTB_Unique_WT_ALLmatrix_Low.png" == name
                for name in aggregate_names
            )
        )
        all_matrix = (
            self.matrices / "1. All Strain Matrices"
            / f"Run001_{date}_ALLmatrix_Low.png"
        )
        dedup_matrix = (
            self.matrices / "2. All Strain Matrices -- No WT Dupe"
            / f"Run001_{date}_E1.0-WTC_E2.A-WTAWTB_Unique_WT_ALLmatrix_Low.png"
        )
        with Image.open(all_matrix) as all_image, Image.open(dedup_matrix) as dedup_image:
            self.assertLess(dedup_image.height, all_image.height)

        self.assertTrue((self.matrices / "3. Per Experiment Matrices" / "Run001_E1_0_Top_Matrix.png").is_file())
        self.assertTrue(
            (
                self.matrices
                / "4. Individual Labelled Crops"
                / "E2"
                / "mut_two"
                / "Run001_E2_A_COND_1_03_Low_mut_two.png"
            ).is_file()
        )
        self.assertFalse(any("COND_1" in path.name for path in aggregate.glob("*")))
        for name, size in original_sizes.items():
            with Image.open(self.crops / name) as image:
                self.assertEqual(image.size, size)

        second = self.run_export()
        self.assertEqual(second["run_id"], "Run002")
        self.assertTrue(all(path.exists() for path in first["published_paths"]))
        log_text = (self.matrices / "Processing Logs" / "Unified Matrix Exports.log").read_text(encoding="utf-8")
        self.assertIn("Run001", log_text)
        self.assertIn("Run002", log_text)

    def test_top_only_does_not_require_low_crops(self) -> None:
        for path in self.crops.glob("*_Low_*.png"):
            path.unlink()
        self.request["selection"]["states"] = ["Top"]
        self.request["outputs"] = ["per-experiment"]
        self.request["preferred_wt"] = None
        result = self.run_export()
        self.assertEqual(result["run_id"], "Run001")
        self.assertEqual(
            sorted(path.name for path in self.matrices.rglob("Run001*.png")),
            [
                "Run001_E1_0_Top_Matrix.png",
                "Run001_E1_0_Top_Matrix.png",
                "Run001_E2_A_Top_Matrix.png",
                "Run001_E2_A_Top_Matrix.png",

            ],
        )
    def test_normalization_off_keeps_separator_variants_as_distinct_wts(self) -> None:
        self.request["outputs"] = ["all-strains", "all-strains-dedup"]
        self.request["normalize_wt_names"] = False
        result = self.run_export()
        self.assertEqual(result["run_id"], "Run001")
        date = datetime.now().strftime("%d.%m.%y")
        all_matrix = (
            self.matrices / "1. All Strain Matrices"
            / f"Run001_{date}_ALLmatrix_Top.png"
        )
        dedup_matrix = (
            self.matrices / "2. All Strain Matrices -- No WT Dupe"
            / (
                f"Run001_{date}_E1.0-WT-AWT-C_E2.A-WT_AWT-B_"
                "Unique_WT_ALLmatrix_Top.png"
            )
        )
        self.assertTrue(dedup_matrix.is_file())
        with Image.open(all_matrix) as all_image, Image.open(dedup_matrix) as dedup_image:
            self.assertEqual(dedup_image.height, all_image.height)


    def test_dataset_presets_and_casefold_collision(self) -> None:
        saved = unified.save_preset(self.config, "My selection", self.request)
        self.assertEqual(saved.parent, self.metadata / "_workflow" / "matrix-presets")
        self.assertEqual(unified.load_preset(self.config, "MY SELECTION"), unified.normalize_request(self.request))
        with self.assertRaises(SystemExit):
            unified.save_preset(self.config, "my selection", self.request)
        with self.assertRaises(SystemExit):
            unified.save_preset(self.config, "../escape", self.request)
        unified.delete_preset(self.config, "MY SELECTION")
        self.assertEqual(unified.preset_names(self.config), [])

    def test_wt_separator_toggle_and_numeric_set_sort(self) -> None:
        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,A,1,1,WT_X\n"
            "E1,2,1,1,WT-X\n",
            encoding="utf-8",
        )
        selection = {
            "groups": [
                {"experiment": "E1", "set": "A", "columns": [1]},
                {"experiment": "E1", "set": "2", "columns": [1]},
            ],
            "conditions": ["COND_1"],
            "states": ["Top"],
        }
        self.assertEqual(
            unified.control_groups_for_selection(self.config, selection, True),
            [("E1", "2"), ("E1", "A")],
        )
        self.assertEqual(
            unified.control_groups_for_selection(self.config, selection, False),
            [("E1", "2"), ("E1", "A")],
        )
        self.assertEqual(unified._control_name("wt-a", True), "WT A")
        self.assertEqual(unified._control_name("WT_A", True), "WT A")
        self.assertNotEqual(unified._control_name("WT-A", False), unified._control_name("WT_A", False))
        self.assertEqual(unified._control_name("wt12", True), "WT12")

    def test_configured_renderer_honours_both_separator_toggle_states(self) -> None:
        enabled = pillow_adapter.configured_copy(
            "all-strains-dedup",
            self.config,
            configured_dir=self.root / "configured-on",
        )
        unified._patch_wt_normalization(enabled, True)
        enabled_text = enabled.read_text(encoding="utf-8")
        self.assertIn('.replace("-", " ")', enabled_text)
        self.assertIn('.replace("_", " ")', enabled_text)
        self.assertIn("control_candidates = {}", enabled_text)

        disabled = pillow_adapter.configured_copy(
            "all-strains-dedup",
            self.config,
            configured_dir=self.root / "configured-off",
        )
        unified._patch_wt_normalization(disabled, False)
        disabled_text = disabled.read_text(encoding="utf-8")
        self.assertNotIn('.replace("-", " ")', disabled_text)
        self.assertNotIn('.replace("_", " ")', disabled_text)
        self.assertIn('suffix[0] in {" ", "-", "_"}', disabled_text)



if __name__ == "__main__":
    unittest.main()
