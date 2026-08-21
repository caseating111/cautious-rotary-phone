from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"


class ControllerContractTests(unittest.TestCase):
    def test_batch_prepares_before_hotkeys_and_pillow_failures_are_checked(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")

        prepare_at = text.index('"--prepare-only"')
        start_ahk_at = text.index("self.start_ahk()", prepare_at)
        self.assertLess(prepare_at, start_ahk_at)
        self.assertIn("started_ahk_here", text)
        self.assertIn("if started_ahk_here:", text)
        self.assertIn("self.stop_ahk()", text)

        pillow_at = text.index("def run_pillow_job")
        pillow_block = text[pillow_at : text.index("def start_ahk", pillow_at)]
        self.assertIn("subprocess.run(", pillow_block)
        self.assertIn("capture_output=True", pillow_block)
        self.assertIn("messagebox.showerror", pillow_block)
        self.assertNotIn("self.launch_python", pillow_block)


if __name__ == "__main__":
    unittest.main()
