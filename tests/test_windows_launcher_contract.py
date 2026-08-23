from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

class WindowsLauncherContractTests(unittest.TestCase):
    def test_controller_is_miniforge_first_with_safe_availability_fallbacks(self) -> None:
        text = (REPO_ROOT / "start_controller.cmd").read_text(encoding="utf-8").lower()
        self.assertIn(r"%userprofile%\.conda\envs\workflow-c\python.exe", text)
        self.assertIn(r"c:\programdata\miniforge3\envs\workflow-c\python.exe", text)
        self.assertIn("-n workflow-c python", text)
        self.assertIn("py -3.11", text)
        self.assertIn("no alternate python was started", text)
        self.assertNotIn("-n cautious-rotary-phone", text)
        self.assertNotIn("-n base", text)
        self.assertNotIn("py -3.14", text)

    def test_custom_matrix_is_miniforge_first_and_uses_same_workflow_environment(self) -> None:
        text = (REPO_ROOT / "start_custom_matrix.cmd").read_text(encoding="utf-8").lower()
        self.assertIn(r"%userprofile%\.conda\envs\workflow-c\python.exe", text)
        self.assertIn("-n workflow-c python", text)
        self.assertIn("py -3.11", text)
        self.assertNotIn("-n cautious-rotary-phone", text)
        self.assertNotIn("py -3.14", text)

    def test_private_launcher_delegates_to_unified_launcher(self) -> None:
        text = (REPO_ROOT / "start_controller_private_test.cmd").read_text(encoding="utf-8").lower()
        self.assertIn('call "%~dp0start_controller.cmd"', text)
        self.assertNotIn("start_controller_no_anaconda.cmd", text)

if __name__ == "__main__":
    unittest.main()