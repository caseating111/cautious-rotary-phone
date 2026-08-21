from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class WindowsLauncherContractTests(unittest.TestCase):
    def test_controller_calls_batch_conda_and_keeps_python_fallbacks(self) -> None:
        text = (REPO_ROOT / "start_controller.cmd").read_text(encoding="utf-8").lower()

        named = "call conda run --no-capture-output -n cautious-rotary-phone python"
        base = "call conda run --no-capture-output -n base python"
        py_launcher = "where py >nul 2>nul"
        path_python = "python tools\\workflow_controller_extended.py"

        self.assertIn(named, text)
        self.assertIn(base, text)
        self.assertIn(py_launcher, text)
        self.assertIn(path_python, text)
        self.assertLess(text.index(named), text.index(base))
        self.assertLess(text.index(base), text.index(py_launcher))

    def test_custom_matrix_launcher_also_calls_conda_batch_entrypoint(self) -> None:
        text = (REPO_ROOT / "start_custom_matrix.cmd").read_text(encoding="utf-8").lower()
        self.assertIn(
            "call conda run --no-capture-output -n cautious-rotary-phone python",
            text,
        )
        self.assertIn("call conda run --no-capture-output -n base python", text)


if __name__ == "__main__":
    unittest.main()
