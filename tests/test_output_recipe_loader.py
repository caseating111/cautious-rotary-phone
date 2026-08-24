from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.output_recipe_loader import default_recipe_folder, load_output_recipe


class OutputRecipeLoaderTests(unittest.TestCase):
    def write_recipe(self, root: Path, display_mode: str) -> Path:
        recipe = root / "recipe.json"
        recipe.write_text(
            json.dumps(
                {
                    "recipe_version": 1,
                    "output_type": "custom matrix",
                    "output_path": "C:/outputs/EXP_4",
                    "display_mode": display_mode,
                    "selection": {
                        "groups": [{"experiment": "E2", "set": "A", "columns": [1, 3]}],
                        "conditions": ["SALT"],
                        "states": ["Top"],
                    },
                }
            ),
            encoding="utf-8",
        )
        return recipe

    def test_raw_recipe_restores_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            loaded = load_output_recipe(self.write_recipe(Path(temp), "raw"))
        self.assertEqual(loaded["display_mode"], "Raw")
        self.assertEqual(loaded["selection"]["groups"][0]["columns"], [1, 3])

    def test_presentation_recipe_fails_explicitly_instead_of_reopening_broken_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit) as caught:
                load_output_recipe(self.write_recipe(Path(temp), "presentation normalized (archived Fiji plate range)"))
        self.assertIn("retired", str(caught.exception).casefold())
        self.assertIn("raw", str(caught.exception).casefold())

    def test_non_custom_recipe_is_not_guessed_into_comparison_builder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            recipe = Path(temp) / "recipe.json"
            recipe.write_text(json.dumps({"recipe_version": 1, "output_type": "all strains", "selection": {}}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                load_output_recipe(recipe)

    def test_default_recipe_folder_is_backend_output_area(self) -> None:
        self.assertEqual(default_recipe_folder("C:/experiment/outputs"), Path("C:/experiment/outputs") / "_workflow" / "output-recipes")


if __name__ == "__main__":
    unittest.main()
