from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_fiji_macro_from_config as fiji_adapter
from tools import four_point_batch as batch_adapter


class NumericConfigGuardTests(unittest.TestCase):
    def test_batch_reports_malformed_json_without_traceback_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            config_path.write_text("{bad json", encoding="utf-8")

            with patch.object(batch_adapter, "CONFIG_FILE", config_path):
                with self.assertRaises(SystemExit) as caught:
                    batch_adapter.load_config(require_fiji=False)

            self.assertIn("Could not read config.json", str(caught.exception))

    def test_fiji_launcher_reports_non_object_config_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            config_path.write_text("[]", encoding="utf-8")

            with self.assertRaises(SystemExit) as caught:
                fiji_adapter.load_config(config_path)

            self.assertIn("JSON object of named settings", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
