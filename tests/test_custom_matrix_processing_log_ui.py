from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUI = REPO_ROOT / "tools" / "custom_matrix_gui_recorded.py"


class CustomMatrixProcessingLogUiTests(unittest.TestCase):
    def test_human_processing_log_is_exposed_without_surfacing_machine_folder(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        self.assertIn('text="Open Processing Logs"', text)
        self.assertIn('Path(self.config_data["matrix_output"]) / "Processing Logs"', text)
        self.assertIn("Processing Log:\\n{human_log}", text)
        self.assertIn("machine recipe was saved separately under _workflow", text)

    def test_missing_log_folder_is_non_blocking_before_first_output(self) -> None:
        text = GUI.read_text(encoding="utf-8")
        start = text.index("def open_processing_logs")
        end = text.index("def open_recipe", start)
        block = text[start:end]
        self.assertIn("if not folder.is_dir()", block)
        self.assertIn("after the first recorded custom output", block)
        self.assertIn("return", block)


if __name__ == "__main__":
    unittest.main()
