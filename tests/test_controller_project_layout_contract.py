from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller_extended.py"


class ControllerProjectLayoutContractTests(unittest.TestCase):
    def test_layout_remains_opt_in_and_reports_folder_move(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('text="Create project layout from Image root"', text)
        self.assertIn('messagebox.askyesno(', text)
        self.assertIn("selected image-root folder itself will be moved intact into Raw", text)
        self.assertIn("Image files are not modified or copied", text)

    def test_layout_configures_output_paths_and_rebases_csvs_moved_with_source(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        start = text.index("def apply_project_layout")
        end = text.index("def initialize_project_layout", start)
        block = text[start:end]
        self.assertIn('self.vars["image_root"].set(str(layout.image_root))', block)
        self.assertIn('self.vars["crop_output"].set(str(layout.crop_output))', block)
        self.assertIn('self.vars["matrix_output"].set(str(layout.matrix_output))', block)
        self.assertIn("project_layout.rebase_moved_path", block)
        self.assertIn("candidate_dirs = [layout.metadata_dir, layout.project_root]", block)

    def test_existing_raw_layout_is_recognized_without_another_move(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn("project_layout.existing_layout_for_raw(source)", text)
        self.assertIn("Recognised existing project layout", text)
        self.assertIn("moved_from = None if layout.image_root == source else source", text)


if __name__ == "__main__":
    unittest.main()
