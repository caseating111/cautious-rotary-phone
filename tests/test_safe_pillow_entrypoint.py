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

    def test_controller_routes_pillow_jobs_through_staging_wrapper(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        pillow_at = text.index("def run_pillow_job")
        pillow_block = text[pillow_at : text.index("def start_ahk", pillow_at)]

        self.assertIn('"run_existing_pillow_from_config.py"', pillow_block)
        self.assertNotIn("run_matrices_from_config.py", text)


if __name__ == "__main__":
    unittest.main()
