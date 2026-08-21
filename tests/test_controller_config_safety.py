from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_controller import DEFAULTS, load_config_state


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = REPO_ROOT / "tools" / "workflow_controller.py"


class ControllerConfigSafetyTests(unittest.TestCase):
    def test_missing_config_uses_defaults_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data, error = load_config_state(Path(temp) / "missing.json")
            self.assertEqual(data, DEFAULTS)
            self.assertIsNone(error)

    def test_malformed_config_is_preserved_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            original = "{broken json"
            path.write_text(original, encoding="utf-8")

            data, error = load_config_state(path)

            self.assertEqual(data, DEFAULTS)
            self.assertIsNotNone(error)
            self.assertIn("has not been overwritten", error or "")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_non_object_config_is_preserved_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            original = json.dumps(["not", "settings"])
            path.write_text(original, encoding="utf-8")

            data, error = load_config_state(path)

            self.assertEqual(data, DEFAULTS)
            self.assertIn("not a JSON object", error or "")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_valid_config_merges_known_values_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(
                json.dumps({"crop_width": 222, "unknown_future_key": "keep out of UI"}),
                encoding="utf-8",
            )

            data, error = load_config_state(path)

            self.assertIsNone(error)
            self.assertEqual(data["crop_width"], "222")
            self.assertNotIn("unknown_future_key", data)

    def test_workflow_actions_do_not_implicitly_replace_unreadable_config(self) -> None:
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('command=lambda: self.save(explicit=True)', text)
        self.assertIn("if not self.save():", text)
        self.assertIn("Action blocked: unreadable existing config preserved.", text)
        self.assertIn("Replace unreadable config?", text)


if __name__ == "__main__":
    unittest.main()
