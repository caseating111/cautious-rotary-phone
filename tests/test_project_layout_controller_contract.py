from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"
START_CONTROLLER = REPO_ROOT / "start_controller_miniforge.cmd"


class ProjectLayoutControllerContractTests(unittest.TestCase):
    def test_extended_controller_exposes_one_root_project_setup(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("project_layout.default_prefix()", text)
        self.assertIn('text="Create project layout from Image root"', text)
        self.assertIn('self.vars["image_root"].set(str(layout.image_root))', text)
        self.assertIn('self.vars["crop_output"].set(str(layout.crop_output))', text)
        self.assertIn('self.vars["matrix_output"].set(str(layout.matrix_output))', text)
        self.assertIn("Image files are not modified or copied", text)
        self.assertIn("ATTEMPT1", text)

    def test_windows_launcher_targets_miniforge_workflow_environment(self) -> None:
        controller = START_CONTROLLER.read_text(encoding="utf-8").lower()
        self.assertIn('conda_default_env%"=="workflow-c', controller)
        self.assertIn(".conda\\envs\\workflow-c\\python.exe", controller)
        self.assertIn("tools\\workflow_controller_extended.py", controller)
        self.assertNotIn("-n base", controller)


if __name__ == "__main__":
    unittest.main()
