from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "start_controller_miniforge.cmd"


class MiniforgeLauncherContractTests(unittest.TestCase):
    def test_launcher_prefers_workflow_c_python_311(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8").lower()
        self.assertIn('conda_default_env%"=="workflow-c', text)
        self.assertIn(".conda\\envs\\workflow-c\\python.exe", text)
        self.assertIn("miniforge3\\envs\\workflow-c\\python.exe", text)
        self.assertIn("python=3.11 pillow pandas openpyxl", text)
        self.assertIn("tools\\workflow_controller_extended.py", text)
        self.assertNotIn("anaconda", text)
        self.assertNotIn("python 3.14", text)

    def test_launcher_applies_private_temp_boundary(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("PRIVATE_ROOT=C:\\LocalWorkflowData", text)
        self.assertIn('set "TEMP=%PRIVATE_WIN_TEMP%"', text)
        self.assertIn("-Djava.io.tmpdir=%PRIVATE_JAVA_TEMP%", text)


if __name__ == "__main__":
    unittest.main()
