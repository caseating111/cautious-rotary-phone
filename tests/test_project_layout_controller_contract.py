from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"
START_CONTROLLER = REPO_ROOT / "start_controller.cmd"
START_PRIVATE = REPO_ROOT / "start_controller_private_test.cmd"


class ProjectLayoutControllerContractTests(unittest.TestCase):
    def test_extended_controller_exposes_one_root_project_setup(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("project_layout.default_prefix()", text)
        self.assertIn('text="Create project layout from Image root"', text)
        self.assertIn('self.vars["image_root"].set(str(layout.image_root))', text)
        self.assertIn('self.vars["crop_output"].set(str(layout.crop_output))', text)
        self.assertIn('self.vars["matrix_output"].set(str(layout.matrix_output))', text)
        self.assertIn("Image files are not modified or copied", text)

    def test_launchers_prefer_the_shared_miniforge_workflow_runtime(self) -> None:
        controller = START_CONTROLLER.read_text(encoding="utf-8").lower()
        private = START_PRIVATE.read_text(encoding="utf-8").lower()
        self.assertIn(r"%userprofile%\.conda\envs\workflow-c\python.exe", controller)
        self.assertIn("-n workflow-c python", controller)
        self.assertIn("py -3.11", controller)
        self.assertNotIn("py -3.14", controller)
        self.assertIn('call "%~dp0start_controller.cmd"', private)
        self.assertNotIn("py -3.14", private)


if __name__ == "__main__":
    unittest.main()
