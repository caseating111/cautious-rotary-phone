from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import finalize_images_reconciliation as finalize
from tools import reconcile_images_csv as reconcile


class MetadataConfigSafetyTests(unittest.TestCase):
    def test_both_helpers_reject_malformed_json_cleanly(self) -> None:
        for helper in (reconcile, finalize):
            with self.subTest(helper=helper.__name__), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "config.json"
                path.write_text("{broken", encoding="utf-8")
                with self.assertRaises(SystemExit) as caught:
                    helper.load_config(path)
                self.assertIn("Could not read config.json", str(caught.exception))

    def test_both_helpers_reject_non_object_json_cleanly(self) -> None:
        for helper in (reconcile, finalize):
            with self.subTest(helper=helper.__name__), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "config.json"
                path.write_text(json.dumps(["not", "settings"]), encoding="utf-8")
                with self.assertRaises(SystemExit) as caught:
                    helper.load_config(path)
                self.assertEqual(
                    str(caught.exception),
                    "config.json must contain a JSON object of named settings.",
                )


if __name__ == "__main__":
    unittest.main()
