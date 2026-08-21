from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"
START_CONTROLLER = REPO_ROOT / "start_controller.cmd"
START_CUSTOM = REPO_ROOT / "start_custom_matrix.cmd"


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

    def test_windows_launchers_call_conda_and_try_anaconda_base_before_system_python(self) -> None:
        controller = START_CONTROLLER.read_text(encoding="utf-8").lower()
        custom = START_CUSTOM.read_text(encoding="utf-8").lower()
        self.assertIn("call conda run", controller)
        self.assertIn("call conda run", custom)
        self.assertIn("-n base python tools\\workflow_controller_extended.py", controller)
        self.assertIn("-n base python tools\\custom_matrix_gui_recorded.py", custom)
        self.assertNotIn("\n    conda run --no-capture-output", controller)
        self.assertNotIn("\n    conda run --no-capture-output", custom)


if __name__ == "__main__":
    unittest.main()
