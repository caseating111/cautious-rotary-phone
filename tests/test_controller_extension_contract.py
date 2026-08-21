from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENDED = REPO_ROOT / "tools" / "workflow_controller_extended.py"
STARTER = REPO_ROOT / "start_controller.cmd"


class ControllerExtensionContractTests(unittest.TestCase):
    def test_extended_controller_adds_only_thin_utility_launchers(self) -> None:
        text = EXTENDED.read_text(encoding="utf-8")
        self.assertIn("class ExtendedController(Controller)", text)
        self.assertIn('text="Custom matrices"', text)
        self.assertIn('tools/custom_matrix_gui_recorded.py', text)
        self.assertIn('text="Preferred WT source"', text)
        self.assertIn('tools/dedup_control_gui.py', text)
        self.assertNotIn("Image.open", text)
        self.assertNotIn("subprocess.run", text)

    def test_windows_starter_uses_extended_controller(self) -> None:
        text = STARTER.read_text(encoding="utf-8")
        self.assertIn("tools\\workflow_controller_extended.py", text)
        self.assertNotIn("tools\\workflow_controller.py", text)


if __name__ == "__main__":
    unittest.main()
