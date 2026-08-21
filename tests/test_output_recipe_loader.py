from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.output_recipe_loader import default_recipe_folder, load_output_recipe


class OutputRecipeLoaderTests(unittest.TestCase):
    def test_custom_matrix_recipe_restores_selection_and_display_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipe = root / "recipe.json"
            recipe.write_text(
                json.dumps(
                    {
                        "recipe_version": 1,
                        "output_type": "custom matrix",
                        "output_path": "C:/outputs/EXP_4",
                        "display_mode": "presentation normalized (archived Fiji plate range)",
                        "selection": {
                            "groups": [{"experiment": "E2", "set": "A", "columns": [1, 3]}],
                            "conditions": ["SALT"],
                            "states": ["Top"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            loaded = load_output_recipe(recipe)
            self.assertEqual(loaded["display_mode"], "Presentation normalized")
            self.assertEqual(loaded["selection"]["groups"][0]["columns"], [1, 3])
            self.assertEqual(loaded["output_path"], "C:/outputs/EXP_4")

    def test_non_custom_recipe_is_not_guessed_into_comparison_builder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            recipe = Path(temp) / "recipe.json"
            recipe.write_text(
                json.dumps({"recipe_version": 1, "output_type": "all strains", "selection": {}}),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as caught:
                load_output_recipe(recipe)
            self.assertIn("custom matrix recipes", str(caught.exception))

    def test_default_recipe_folder_is_backend_output_area(self) -> None:
        self.assertEqual(
            default_recipe_folder("C:/experiment/outputs"),
            Path("C:/experiment/outputs") / "_workflow" / "output-recipes",
        )


if __name__ == "__main__":
    unittest.main()
