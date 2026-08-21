from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import custom_matrix_selection as custom
from tools import run_existing_pillow_from_config as pillow_adapter


class CustomMatrixSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.grid = self.root / "grid.csv"
        self.images = self.root / "images.csv"
        self.conditions = self.root / "condition_order.csv"
        self.crops = self.root / "crops"
        self.outputs = self.root / "outputs"
        self.crops.mkdir()

        self.grid.write_text(
            "Experiment,Set,GridCols,Column,Strain\n"
            "E1,S0,3,1,alpha\n"
            "E1,S0,3,2,beta\n"
            "E1,S0,3,3,gamma\n"
            "E2,A,4,1,wt\n"
            "E2,A,4,2,delta\n"
            "E2,A,4,3,epsilon\n"
            "E2,A,4,4,zeta\n",
            encoding="utf-8",
        )
        self.images.write_text(
            "Filename,Experiment,Set,Type\n"
            "plate1.jpg,E1,S0,YPDA\n"
            "plate2.jpg,E1,S0,SALT\n"
            "plate3.jpg,E2,A,YPDA\n"
            "plate4.jpg,E2,A,SALT\n",
            encoding="utf-8",
        )
        self.conditions.write_text("Type,Order\nYPDA,1\nSALT,2\n", encoding="utf-8")
        self.config = {
            "crop_output": str(self.crops),
            "matrix_output": str(self.outputs),
            "grid_csv": str(self.grid),
            "images_csv": str(self.images),
            "condition_order_csv": str(self.conditions),
            "crop_width": 130,
            "crop_height": 546,
        }
        self.selection = {
            "groups": [
                {"experiment": "E1", "set": "S0", "columns": [1, 3]},
                {"experiment": "E2", "set": "A", "columns": [2, 4]},
            ],
            "conditions": ["SALT"],
            "states": ["Top"],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_filter_project_csvs_keeps_only_selected_groups_columns_and_conditions(self) -> None:
        filtered = custom.filter_project_csvs(self.config, self.selection, self.root / "filtered")
        grid_rows = custom.read_rows(filtered["grid_csv"])[1]
        image_rows = custom.read_rows(filtered["images_csv"])[1]
        condition_rows = custom.read_rows(filtered["condition_order_csv"])[1]

        self.assertEqual(
            [(row["Experiment"], row["Set"], row["Column"]) for row in grid_rows],
            [("E1", "S0", "1"), ("E1", "S0", "3"), ("E2", "A", "2"), ("E2", "A", "4")],
        )
        self.assertEqual([row["Filename"] for row in image_rows], ["plate2.jpg", "plate4.jpg"])
        self.assertEqual([row["Type"] for row in condition_rows], ["SALT"])

    def test_selection_rejects_unknown_column_before_pillow_run(self) -> None:
        bad = json.loads(json.dumps(self.selection))
        bad["groups"][0]["columns"] = [99]
        with self.assertRaises(SystemExit) as caught:
            custom.filter_project_csvs(self.config, bad, self.root / "filtered")
        self.assertIn("E1/S0 column 99", str(caught.exception))

    def test_patch_matrix_states_only_changes_generated_copy(self) -> None:
        script = self.root / "configured.py"
        script.write_text('STATES_TO_BUILD = ["Top", "Low"]\n', encoding="utf-8")
        custom.patch_matrix_states(script, ["Low"])
        self.assertEqual(script.read_text(encoding="utf-8"), "STATES_TO_BUILD = ['Low']\n")

    def test_selected_contract_requires_only_selected_crop_cells(self) -> None:
        filtered = custom.filter_project_csvs(self.config, self.selection, self.root / "filtered")
        contract = pillow_adapter.expected_crop_contract(filtered["grid_csv"], filtered["images_csv"])
        self.assertEqual(len(contract), 8)
        self.assertTrue(all("_salt_" in key for key in contract))
        self.assertTrue(any("e1_s0_salt_01_top_" in key for key in contract))
        self.assertFalse(any("_ypda_" in key for key in contract))

    def test_output_postcondition_rejects_missing_selected_matrix(self) -> None:
        output = self.root / "partial"
        output.mkdir()
        (output / "E1_S0_Top_MATRIX.png").write_bytes(b"placeholder")

        with self.assertRaises(SystemExit) as caught:
            custom.validate_matrix_outputs(output, self.selection)
        self.assertIn("E2_A_Top_MATRIX.png", str(caught.exception))
        self.assertIn("Partial output was left for inspection", str(caught.exception))

    def test_end_to_end_builds_only_selected_top_matrices_from_existing_crops(self) -> None:
        # The custom route intentionally works from already-existing crops; source images are not needed here.
        for exp, set_name, columns in (("E1", "S0", [(1, "alpha"), (3, "gamma")]), ("E2", "A", [(2, "delta"), (4, "zeta")])):
            for column, strain in columns:
                for state in ("Top", "Low"):
                    path = self.crops / f"{exp}_{set_name}_SALT_{column:02d}_{state}_{strain}.png"
                    Image.new("L", (130, 546), column * 20).save(path)

        app_dir = self.root / "app"
        config_file = app_dir / "config.json"
        app_dir.mkdir()
        config_file.write_text(json.dumps(self.config), encoding="utf-8")

        with patch.object(custom, "APP_DIR", app_dir), patch.object(custom, "LAST_SELECTION_FILE", app_dir / "last_matrix_selection.json"), patch.object(
            pillow_adapter, "APP_DIR", app_dir
        ), patch.object(pillow_adapter, "CONFIG_FILE", config_file), patch.object(
            pillow_adapter, "LAST_OUTPUT_FILE", app_dir / "last_pillow_output.txt"
        ):
            output = custom.run_selection(self.selection, no_open_output=True)

        produced = sorted(path.name for path in output.glob("*.png"))
        self.assertEqual(produced, ["E1_S0_Top_MATRIX.png", "E2_A_Top_MATRIX.png"])
        self.assertTrue((app_dir / "last_matrix_selection.json").is_file())


if __name__ == "__main__":
    unittest.main()