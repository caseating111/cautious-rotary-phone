from __future__ import annotations

import json
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
            state = Path(temp) / "legacy-state.txt"
            with patch.object(batch_adapter, "CONFIGURED_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ), patch.object(batch_adapter, "LEGACY_STATE_FILE", state):
                built = batch_adapter.build_macro(config)

            text = built.read_text(encoding="utf-8")
            self.assertIn('gridFile   = "C:/project/grid.csv";', text)
            self.assertIn(str(pending).replace("\\", "/"), text)
            self.assertIn(str(state).replace("\\", "/"), text)
            self.assertIn('inputRoot  = "C:/project/images";', text)
            self.assertIn('outputRoot = "C:/project/crops";', text)
            self.assertIn("CROP_W = 140;", text)
            self.assertIn("CROP_H = 560;", text)
            self.assertIn("tolerance=0.05", text)
            self.assertIn("folders = getFileList(inputRoot);", text)
            self.assertIn("runMacro(", text)
            self.assertNotIn("1 / 4 — R1C1", text)
            self.assertNotIn("4 / 4 — R5C", text)

    def test_four_point_fallback_only_configures_existing_macro(self) -> None:
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
            output = Path(temp) / "legacy.ijm"
            pending = Path(temp) / "pending_images.csv"
            state = Path(temp) / "legacy-state.txt"
            with patch.object(batch_adapter, "CONFIGURED_LEGACY_MACRO", output), patch.object(
                batch_adapter, "PENDING_IMAGES_CSV", pending
            ), patch.object(batch_adapter, "LEGACY_STATE_FILE", state):
                built = batch_adapter.build_legacy_macro(config)

            text = built.read_text(encoding="utf-8")
            self.assertIn('gridFile   = "C:/project/grid.csv";', text)
            self.assertIn(str(pending).replace("\\", "/"), text)
            self.assertIn(str(state).replace("\\", "/"), text)
            self.assertIn('inputRoot  = "C:/project/images";', text)
            self.assertIn('outputRoot = "C:/project/crops";', text)
            self.assertIn("CROP_W = 140;", text)
            self.assertIn("CROP_H = 560;", text)
            self.assertIn("1 / 4 — R1C1", text)
            self.assertIn("4 / 4 — R5C", text)
            self.assertNotIn("FULL-COLUMN COMPOSED ROUTE", text)
            self.assertNotIn('"path here"', text)

    def test_four_point_fallback_rejects_grid_width_outside_original_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            grid = Path(temp) / "grid.csv"
            grid.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,8,1,WT\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as caught:
                batch_adapter.validate_legacy_grid_widths({"grid_csv": str(grid)})
            self.assertIn("only supports its original 10- or 12-column grids", str(caught.exception))

    def test_prepare_only_config_does_not_require_fiji_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "image_root": "C:/project/images",
                        "crop_output": "C:/project/crops",
                        "grid_csv": "C:/project/grid.csv",
                        "images_csv": "C:/project/images.csv",
                        "condition_order_csv": "C:/project/condition_order.csv",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(batch_adapter, "CONFIG_FILE", config_path):
                prepared = batch_adapter.load_config(require_fiji=False)
                self.assertNotIn("fiji_executable", prepared)
                with self.assertRaises(SystemExit) as caught:
                    batch_adapter.load_config(require_fiji=True)
            self.assertIn("fiji_executable", str(caught.exception))

    def test_batch_runtime_precheck_keeps_prepare_only_independent_of_fiji(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            required = [root / name for name in ("source.ijm", "align.ijm", "crop.ijm", "validate.py", "preflight.py")]
            for path in required:
                path.write_text("placeholder\n", encoding="utf-8")

            config = {"fiji_executable": str(root / "missing-fiji.exe")}
            patches = [
                patch.object(batch_adapter, "SOURCE_MACRO", required[0]),
                patch.object(batch_adapter, "ALIGNMENT_MACRO", required[1]),
                patch.object(batch_adapter, "CROP_HELPER", required[2]),
                patch.object(batch_adapter, "VALIDATOR", required[3]),
                patch.object(batch_adapter, "PREFLIGHT", required[4]),
            ]
            for item in patches:
                item.start()
            try:
                batch_adapter.validate_runtime_files(config, require_fiji=False)
                batch_adapter.validate_runtime_files(config, require_fiji=False, legacy=True)
                with self.assertRaises(SystemExit) as caught:
                    batch_adapter.validate_runtime_files(config, require_fiji=True)
                self.assertIn("Fiji executable not found", str(caught.exception))
            finally:
                for item in reversed(patches):
                    item.stop()

    def test_pillow_wrapper_stops_on_project_validator_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            validator = root / "validator.py"
            validator.write_text(
                "print('synthetic invalid metadata')\nraise SystemExit(1)\n",
                encoding="utf-8",
            )
            config = {
                "grid_csv": str(root / "grid.csv"),
                "images_csv": str(root / "images.csv"),
                "condition_order_csv": str(root / "condition_order.csv"),
            }
            with patch.object(pillow_adapter, "VALIDATOR", validator):
                with self.assertRaises(SystemExit) as caught:
                    pillow_adapter.validate_csvs(config)
            self.assertIn("synthetic invalid metadata", str(caught.exception))

    def test_matrix_output_cannot_live_inside_recursive_crop_input_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop_root = root / "crops"
            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_output_layout(crop_root, crop_root / "matrices")
            self.assertIn("Matrix output must be outside crop_output", str(caught.exception))

            pillow_adapter.validate_output_layout(crop_root, root / "matrices")

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

    def test_scoped_orientation_rejects_bad_current_crop_but_ignores_unrelated_png(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / "E1_A_YPDA_01_Top_WT.png"
            unrelated = root / "notes.png"
            Image.new("L", (100, 100), 10).save(selected)
            Image.new("L", (100, 100), 20).save(unrelated)

            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.normalize_crop_orientation(
                    root, 130, 546, paths=[selected], strict=True
                )
            self.assertIn("Current crop inputs have dimensions", str(caught.exception))

            result = pillow_adapter.normalize_crop_orientation(
                root, 130, 546, paths=[], strict=True
            )
            self.assertEqual(result, (0, 0, 0))

    def test_pillow_input_guard_rejects_multiple_files_for_one_logical_cell(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop_root = root / "crops"
            (crop_root / "old").mkdir(parents=True)
            (crop_root / "current").mkdir()
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
            Image.new("L", (546, 130), 10).save(crop_root / "old" / "E1_A_YPDA_01_Top_old.png")
            Image.new("L", (546, 130), 20).save(crop_root / "current" / "E1_A_YPDA_01_Top_WT.png")

            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_unique_crop_matches(crop_root, grid_csv, images_csv)

            message = str(caught.exception)
            self.assertIn("Ambiguous crop inputs", message)
            self.assertIn("old/E1_A_YPDA_01_Top_old.png", message)
            self.assertIn("current/E1_A_YPDA_01_Top_WT.png", message)

    def test_pillow_input_guard_rejects_lone_stale_strain_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop_root = root / "crops"
            crop_root.mkdir()
            grid_csv = root / "grid.csv"
            images_csv = root / "images.csv"
            grid_csv.write_text(
                "Experiment,Set,GridCols,Column,Strain\n"
                "E1,A,1,1,WT_NEW\n",
                encoding="utf-8",
            )
            images_csv.write_text(
                "Filename,Experiment,Set,Type\n"
                "plate1.jpg,E1,A,YPDA\n",
                encoding="utf-8",
            )
            stale = crop_root / "E1_A_YPDA_01_Top_WT_OLD.png"
            Image.new("L", (546, 130), 10).save(stale)

            with self.assertRaises(SystemExit) as caught:
                pillow_adapter.validate_unique_crop_matches(
                    crop_root, grid_csv, images_csv, allow_missing=True
                )

            message = str(caught.exception)
            self.assertIn("Stale crop filename mismatch", message)
            self.assertIn("expected: E1_A_YPDA_01_Top_WT_NEW.png", message)
            self.assertIn("found:    E1_A_YPDA_01_Top_WT_OLD.png", message)

    def test_pillow_input_guard_returns_only_current_logical_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop_root = root / "crops"
            crop_root.mkdir()
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
            top = crop_root / "E1_A_YPDA_01_Top_WT.png"
            low = crop_root / "E1_A_YPDA_01_Low_WT.png"
            unrelated = crop_root / "notes.png"
            Image.new("L", (546, 130), 10).save(top)
            Image.new("L", (546, 130), 20).save(low)
            Image.new("L", (100, 100), 30).save(unrelated)

            selected = pillow_adapter.validate_unique_crop_matches(crop_root, grid_csv, images_csv)
            self.assertEqual(selected, sorted([top, low]))
            self.assertNotIn(unrelated, selected)


if __name__ == "__main__":
    unittest.main()
