from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.metadata_review_gui import configured_images_csv


class MetadataGuiConfigTests(unittest.TestCase):
    def test_valid_object_returns_images_csv_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text(json.dumps({"images_csv": "C:/project/images.csv"}), encoding="utf-8")
            self.assertEqual(configured_images_csv(config), Path("C:/project/images.csv"))

    def test_non_object_config_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                configured_images_csv(config)
            self.assertIn("JSON object", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
