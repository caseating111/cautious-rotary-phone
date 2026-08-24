from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUI = REPO_ROOT / "tools" / "custom_matrix_gui_recorded.py"


class CustomMatrixProcessingLogUiTests(unittest.TestCase):
    def test_run_surfaces_human_log_and_machine_recipe_paths(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        self.assertIn('text="Open Processing Logs"', text)
        self.assertIn('Path(self.config_data["matrix_output"]) / "Processing Logs"', text)
        self.assertIn("Processing Log:\\n{log}", text)
        self.assertIn("Machine recipe:\\n{recipe}", text)

    def test_missing_log_folder_is_non_blocking_before_first_output(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        start = text.index("def open_processing_logs")
        end = text.index("def open_recipe", start)
        block = text[start:end]
        self.assertIn("if not folder.is_dir()", block)
        self.assertIn("after the first recorded output run", block)
        self.assertIn("return", block)


if __name__ == "__main__":
    unittest.main()
