from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"
OBSOLETE_DIRECT_LAUNCHER = REPO_ROOT / "tools" / "run_matrices_from_config.py"
SAFE_WRAPPER = REPO_ROOT / "tools" / "run_existing_pillow_from_config.py"


class SafePillowEntrypointTests(unittest.TestCase):
    def test_obsolete_direct_matrix_launcher_stays_removed(self) -> None:
        self.assertFalse(OBSOLETE_DIRECT_LAUNCHER.exists())
        self.assertTrue(SAFE_WRAPPER.is_file())

    def test_controller_routes_outputs_to_the_unified_recorded_applet(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('self.launch_python("tools/custom_matrix_gui_recorded.py")', text)
        self.assertNotIn("run_matrices_from_config.py", text)
        self.assertNotIn("def run_pillow_job", text)


if __name__ == "__main__":
    unittest.main()
